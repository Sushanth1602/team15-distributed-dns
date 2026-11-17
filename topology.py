import sys
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel


class DNSTopo(Topo):
    def build(self, server_count=5):
        self.addHost('client', ip='10.0.0.1/24')
        self.addHost('resolver', ip='10.0.0.53/24')
        self.addHost('monitor', ip='10.0.0.100/24',
                     inNamespace=False)

        servers = []
        for i in range(1, server_count + 1):
            servers.append(
                self.addHost(f'dns{i}', ip=f'10.0.0.{10+i}/24')
            )

        switch = self.addSwitch('s1', protocols='OpenFlow13')

        for host in ['client', 'resolver', 'monitor'] + servers:
            self.addLink(host, switch)


def run():
    server_count = int(sys.argv[1]) if len(sys.argv) > 1 else 5

    if server_count not in (1, 3, 5):
        raise ValueError("Server count must be 1, 3, or 5")

    topo = DNSTopo(server_count=server_count)
    net = Mininet(topo=topo, controller=None,
                  switch=OVSSwitch, autoSetMacs=True)

    net.addController('c0', controller=RemoteController,
                      ip='127.0.0.1', port=6653)

    net.start()
    print(f"Topology started with {server_count} DNS servers")
    CLI(net)
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    run()
