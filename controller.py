import json
import os
import time

from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import (
    CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
)
from os_ken.ofproto import ofproto_v1_3
from os_ken.lib.packet import (
    packet, ethernet, ether_types, ipv4, udp
)
from os_ken.lib import hub


class DNSController(app_manager.OSKenApp):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    HEARTBEAT_FILE = "/tmp/team15_heartbeats.json"
    HEARTBEAT_TIMEOUT = 3

    VIRTUAL_IP = "10.0.0.53"
    VIRTUAL_PORT = 5353
    MONITOR_IP = "10.0.0.100"
    HEARTBEAT_PORT = 9999

    DNS_SERVERS = [
         f"10.0.0.{10+i}" for i in range(1, 6)
    ]

    def __init__(self, *args, **kwargs):
        super(DNSController, self).__init__(*args, **kwargs)

        self.mac_to_port = {}
        self.server_health = {ip: False for ip in self.DNS_SERVERS}
        self.server_locations = {}
        self.round_robin_index = 0
        self.query_counts = {ip: 0 for ip in self.DNS_SERVERS}

        self.monitor_thread = hub.spawn(self.monitor_heartbeats)
        self.logger.info("DNS SDN Controller started")

    def monitor_heartbeats(self):
        while True:
            try:
                with open(self.HEARTBEAT_FILE) as f:
                    heartbeats = json.load(f)

                now = time.time()

                for ip in self.DNS_SERVERS:
                    timestamp = heartbeats.get(ip)
                    healthy = (
                        timestamp is not None
                        and now - float(timestamp) <= self.HEARTBEAT_TIMEOUT
                    )

                    previous = self.server_health[ip]

                    if healthy and not previous:
                        self.logger.info("%s RECOVERED", ip)
                    elif not healthy and previous:
                        self.logger.warning("%s FAILED", ip)

                    self.server_health[ip] = healthy

            except (OSError, ValueError, TypeError) as error:
                self.logger.warning("Heartbeat read error: %s", error)

            hub.sleep(1)

    def get_healthy_servers(self):
        return [
            ip for ip in self.DNS_SERVERS
            if self.server_health[ip] and ip in self.server_locations
        ]

    def install_controller_rule(self, dp, priority, match):
        parser = dp.ofproto_parser
        ofp = dp.ofproto

        dp.send_msg(parser.OFPFlowMod(
            datapath=dp,
            priority=priority,
            match=match,
            instructions=[
                parser.OFPInstructionActions(
                    ofp.OFPIT_APPLY_ACTIONS,
                    [parser.OFPActionOutput(
                        ofp.OFPP_CONTROLLER,
                        ofp.OFPCML_NO_BUFFER
                    )]
                )
            ]
        ))

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features(self, ev):
        dp = ev.msg.datapath
        parser = dp.ofproto_parser

        # Send every virtual DNS query to the controller.
        self.install_controller_rule(
            dp, 100,
            parser.OFPMatch(
                eth_type=ether_types.ETH_TYPE_IP,
                ip_proto=17,
                ipv4_dst=self.VIRTUAL_IP,
                udp_dst=self.VIRTUAL_PORT
            )
        )

        # Send heartbeat packets to the controller for server learning.
        self.install_controller_rule(
            dp, 90,
            parser.OFPMatch(
                eth_type=ether_types.ETH_TYPE_IP,
                ip_proto=17,
                ipv4_dst=self.MONITOR_IP,
                udp_dst=self.HEARTBEAT_PORT
            )
        )

        # Table-miss rule.
        self.install_controller_rule(
            dp, 0, parser.OFPMatch()
        )

        self.logger.info("OpenFlow 1.3 switch connected; DNS interception enabled")

    def learn_source(self, dp, in_port, eth, ip_packet):
        dpid = dp.id
        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][eth.src] = in_port

        if ip_packet and ip_packet.src in self.DNS_SERVERS:
            self.server_locations[ip_packet.src] = (eth.src, in_port)

    def normal_forward(self, msg, eth, in_port):
        dp = msg.datapath
        parser = dp.ofproto_parser
        ofp = dp.ofproto

        dpid = dp.id
        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][eth.src] = in_port

        out_port = self.mac_to_port[dpid].get(
            eth.dst, ofp.OFPP_FLOOD
        )

        actions = [parser.OFPActionOutput(out_port)]

        if out_port != ofp.OFPP_FLOOD:
            match = parser.OFPMatch(
                in_port=in_port,
                eth_dst=eth.dst
            )
            dp.send_msg(parser.OFPFlowMod(
                datapath=dp,
                priority=1,
                match=match,
                instructions=[
                    parser.OFPInstructionActions(
                        ofp.OFPIT_APPLY_ACTIONS, actions
                    )
                ]
            ))

        data = msg.data if msg.buffer_id == ofp.OFP_NO_BUFFER else None

        dp.send_msg(parser.OFPPacketOut(
            datapath=dp,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=data
        ))

    def redirect_dns(self, msg, eth, ip_packet):
        dp = msg.datapath
        parser = dp.ofproto_parser
        ofp = dp.ofproto

        healthy = self.get_healthy_servers()

        if not healthy:
            self.logger.warning("No healthy DNS servers available; dropping query")
            return

        selected_ip = healthy[
            self.round_robin_index % len(healthy)
        ]
        self.round_robin_index += 1
        self.query_counts[selected_ip] += 1
        self.logger.info("SERVER LOAD: %s = %d queries",
                          selected_ip, self.query_counts[selected_ip])

        server_mac, server_port = self.server_locations[selected_ip]

        actions = [
            parser.OFPActionSetField(eth_dst=server_mac),
            parser.OFPActionSetField(ipv4_dst=selected_ip),
            parser.OFPActionOutput(server_port)
        ]

        data = msg.data if msg.buffer_id == ofp.OFP_NO_BUFFER else None

        dp.send_msg(parser.OFPPacketOut(
            datapath=dp,
            buffer_id=msg.buffer_id,
            in_port=msg.match["in_port"],
            actions=actions,
            data=data
        ))

        self.logger.info(
            "DNS REDIRECT: %s -> %s (port %s)",
            self.VIRTUAL_IP, selected_ip, server_port
        )

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in(self, ev):
        msg = ev.msg
        pkt = packet.Packet(msg.data)

        eth = pkt.get_protocol(ethernet.ethernet)
        if eth is None or eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        ip_packet = pkt.get_protocol(ipv4.ipv4)
        udp_packet = pkt.get_protocol(udp.udp)

        in_port = msg.match["in_port"]

        # Learn server MAC address and switch port from heartbeat packets.
        self.learn_source(
            msg.datapath, in_port, eth, ip_packet
        )

        if (
            ip_packet is not None
            and udp_packet is not None
            and ip_packet.dst == self.VIRTUAL_IP
            and udp_packet.dst_port == self.VIRTUAL_PORT
        ):
            self.redirect_dns(msg, eth, ip_packet)
            return

        self.normal_forward(msg, eth, in_port)
