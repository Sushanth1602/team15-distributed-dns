import json
import os
import time

from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import (
    CONFIG_DISPATCHER,
    MAIN_DISPATCHER,
    set_ev_cls
)
from os_ken.ofproto import ofproto_v1_3
from os_ken.lib.packet import packet, ethernet, ether_types
from os_ken.lib import hub


class DNSController(app_manager.OSKenApp):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    HEARTBEAT_FILE = "/tmp/team15_heartbeats.json"
    HEARTBEAT_TIMEOUT = 3

    DNS_SERVERS = ["10.0.0.11", "10.0.0.12", "10.0.0.13", "10.0.0.14", "10.0.0.15"]

    def __init__(self, *args, **kwargs):
        super(DNSController, self).__init__(*args, **kwargs)

        self.mac_to_port = {}

        self.server_health = {
            server: False for server in self.DNS_SERVERS
        }

        self.last_seen = {}

        self.monitor_thread = hub.spawn(
            self.monitor_heartbeats
        )

        self.logger.info("DNS SDN Controller started")

    def monitor_heartbeats(self):
        while True:
            try:
                if os.path.exists(self.HEARTBEAT_FILE):
                    with open(self.HEARTBEAT_FILE, "r") as f:
                        heartbeats = json.load(f)

                    now = time.time()

                    for server in self.DNS_SERVERS:
                        timestamp = heartbeats.get(server)

                        if timestamp is None:
                            continue

                        self.last_seen[server] = float(timestamp)

                        healthy = (
                            now - float(timestamp)
                            <= self.HEARTBEAT_TIMEOUT
                        )

                        previous = self.server_health[server]

                        if healthy and not previous:
                            self.logger.info(
                                "%s RECOVERED", server
                            )

                        elif not healthy and previous:
                            self.logger.warning(
                                "%s FAILED - removing from healthy pool",
                                server
                            )

                        self.server_health[server] = healthy

                    for server in self.DNS_SERVERS:
                        timestamp = self.last_seen.get(server)

                        if timestamp is not None:
                            if now - timestamp > self.HEARTBEAT_TIMEOUT:
                                if self.server_health[server]:
                                    self.logger.warning(
                                        "%s FAILED", server
                                    )

                                self.server_health[server] = False

            except Exception as error:
                self.logger.error(
                    "Heartbeat monitoring error: %s", error
                )

            hub.sleep(1)

    def get_healthy_servers(self):
        return [
            server for server in self.DNS_SERVERS
            if self.server_health[server]
        ]

    @set_ev_cls(
        ofp_event.EventOFPSwitchFeatures,
        CONFIG_DISPATCHER
    )
    def switch_features(self, ev):
        dp = ev.msg.datapath
        parser = dp.ofproto_parser
        ofp = dp.ofproto

        match = parser.OFPMatch()

        actions = [
            parser.OFPActionOutput(
                ofp.OFPP_CONTROLLER,
                ofp.OFPCML_NO_BUFFER
            )
        ]

        dp.send_msg(
            parser.OFPFlowMod(
                datapath=dp,
                priority=0,
                match=match,
                instructions=[
                    parser.OFPInstructionActions(
                        ofp.OFPIT_APPLY_ACTIONS,
                        actions
                    )
                ]
            )
        )

        self.logger.info("OpenFlow 1.3 switch connected")

    @set_ev_cls(
        ofp_event.EventOFPPacketIn,
        MAIN_DISPATCHER
    )
    def packet_in(self, ev):
        msg = ev.msg
        dp = msg.datapath
        parser = dp.ofproto_parser
        ofp = dp.ofproto

        in_port = msg.match["in_port"]

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        if eth is None:
            return

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        dpid = dp.id

        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][eth.src] = in_port

        out_port = self.mac_to_port[dpid].get(
            eth.dst,
            ofp.OFPP_FLOOD
        )

        actions = [
            parser.OFPActionOutput(out_port)
        ]

        if out_port != ofp.OFPP_FLOOD:
            match = parser.OFPMatch(
                in_port=in_port,
                eth_dst=eth.dst
            )

            dp.send_msg(
                parser.OFPFlowMod(
                    datapath=dp,
                    priority=1,
                    match=match,
                    instructions=[
                        parser.OFPInstructionActions(
                            ofp.OFPIT_APPLY_ACTIONS,
                            actions
                        )
                    ]
                )
            )

        data = None

        if msg.buffer_id == ofp.OFP_NO_BUFFER:
            data = msg.data

        dp.send_msg(
            parser.OFPPacketOut(
                datapath=dp,
                buffer_id=msg.buffer_id,
                in_port=in_port,
                actions=actions,
                data=data
            )
        )
