from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel


class DNSTopo(Topo):
    def build(self):
        # Client and virtual DNS resolver
        client = self.addHost('client', ip='10.0.0.1/24')
        resolver = self.addHost('resolver', ip='10.0.0.53/24')

        # Heartbeat monitor (shares the Ubuntu network namespace)
        monitor = self.addHost(
            'monitor',
            ip='10.0.0.100/24',
            inNamespace=False
        )

        # Five DNS servers
        servers = []

        for i in range(1, 6):
            servers.append(
                self.addHost(
                    f'dns{i}',
                    ip=f'10.0.0.{10+i}/24'
                )
            )

        # OpenFlow 1.3 switch
        switch = self.addSwitch(
            's1',
            protocols='OpenFlow13'
        )

        # Connect client, resolver and monitor
        self.addLink(client, switch)
        self.addLink(resolver, switch)
        self.addLink(monitor, switch)

        # Connect all DNS servers
        for server in servers:
            self.addLink(server, switch)


def run():
    topo = DNSTopo()

    net = Mininet(
        topo=topo,
        controller=None,
        switch=OVSSwitch,
        autoSetMacs=True
    )

    net.addController(
        'c0',
        controller=RemoteController,
        ip='127.0.0.1',
        port=6653
    )

    net.start()
    CLI(net)
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    run()

