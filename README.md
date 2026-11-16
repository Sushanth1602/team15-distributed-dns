# Team 15 - Distributed DNS-Like Name Resolution System

A DNS-like name resolution system developed using UDP, Python, Mininet,
Open vSwitch and an SDN controller using OS-Ken and OpenFlow 1.3.

## Features

- UDP-based DNS-like query and response communication.
- Multiple DNS servers.
- Round-robin DNS server selection.
- Heartbeat-based server health monitoring.
- Automatic server failure detection.
- Failover to healthy DNS servers.
- Client-side DNS caching and TTL expiration.
- Retry and timeout handling.
- SDN-controlled traffic redirection.
- Performance evaluation for 1, 3 and 5 DNS servers.

## Project Structure

app/
  client.py
  server.py
  resolver.py
  records/

config/
  config.json

controller.py
topology.py

scripts/
  heartbeat_receiver.py
  start_network.sh

tests/
  test_basic.py
  test_cache.py
  test_resolver_integration.py
  test_resolver_unit.py

experiments/
  load_generator.py
  generate_graphs.py

docs/
results/

## Requirements

- Ubuntu 24.04 recommended for the documented Mininet setup
- Python 3
- Mininet
- Open vSwitch
- OS-Ken
- pytest
- pandas
- matplotlib

## 1. Clone the Repository

git clone https://github.com/Sushanth1602/team15-distributed-dns.git
cd team15-distributed-dns

## 2. Install System Dependencies

sudo apt update

sudo apt install -y git python3 python3-pip python3-venv
sudo apt install -y mininet openvswitch-switch

Start Open vSwitch:

sudo systemctl start openvswitch-switch

## 3. Create Python Environment

python3 -m venv .venv

source .venv/bin/activate

python -m pip install --upgrade pip

python -m pip install pytest pandas matplotlib os-ken

Check OS-Ken:

python -c "import os_ken; print('OS-Ken installed')"

## 4. Run Automated Tests

Run the basic UDP tests:

python3 tests/test_basic.py

Run cache tests:

python3 -m pytest tests/test_cache.py -v

Run resolver integration tests:

python3 -m pytest tests/test_resolver_integration.py -v

Run resolver unit tests:

python3 -m pytest tests/test_resolver_unit.py -v

## 5. Start the SDN Controller

Open Terminal 1:

cd team15-distributed-dns

source .venv/bin/activate

osken-manager controller.py --ofp-tcp-listen-port 6653

Keep the controller running.

The controller uses OpenFlow 1.3.

## 6. Start Mininet

Open Terminal 2:

cd team15-distributed-dns

sudo mn -c

sudo python3 topology.py 5

The topology supports:

- 1 DNS server
- 3 DNS servers
- 5 DNS servers

At the Mininet prompt:

pingall

All hosts should be reachable.

## 7. Start Heartbeat Receiver

After the Mininet topology starts, open Terminal 3:

cd team15-distributed-dns

python3 scripts/heartbeat_receiver.py

The monitor host uses:

10.0.0.100

Heartbeat UDP port:

9999

Keep this terminal running.

## 8. Start DNS Servers

At the Mininet prompt, start the five DNS servers:

dns1 python3 app/server.py s1 5353 app/records/server1.json &

dns2 python3 app/server.py s2 5353 app/records/server2.json &

dns3 python3 app/server.py s3 5353 app/records/server3.json &

dns4 python3 app/server.py s4 5353 app/records/server4.json &

dns5 python3 app/server.py s5 5353 app/records/server5.json &

Wait for heartbeat messages and healthy-server learning.

## 9. Test DNS Resolution

At the Mininet prompt:

client python3 app/client.py video.lab

Test an unknown domain:

client python3 app/client.py unknown.lab

Expected results:

video.lab -> status OK

unknown.lab -> status NOT_FOUND

Repeat a successful query before TTL expiry to test client caching.

In the Mininet integration, the SDN controller intercepts queries
addressed to the virtual DNS IP and redirects them to DNS servers.
The application-level resolver module is also used by local tests
and performance experiments.

## 10. Test Server Failure and Recovery

Stop DNS3:

dns3 pkill -f app/server.py

Wait longer than the heartbeat timeout.

Issue a fresh query:

client python3 app/client.py video.lab

The controller should detect DNS3 failure and select another
healthy DNS server.

Restart DNS3:

dns3 python3 app/server.py s3 5353 app/records/server3.json &

Wait for fresh heartbeats and verify recovery in the controller log.

Use fresh queries so an earlier client cache entry does not hide
the network behavior.

## 11. Performance Evaluation

Run the localhost performance experiments with:

python3 experiments/load_generator.py --servers 1 --queries 100

python3 experiments/load_generator.py --servers 3 --queries 100

python3 experiments/load_generator.py --servers 5 --queries 100

Run a missing-domain experiment:

python3 experiments/load_generator.py --servers 3 --queries 100 --scenario missing

Generate graphs:

python3 experiments/generate_graphs.py

Results are stored in results/raw/ and results/.

These localhost experiments are application-level sequential
measurements. They are not concurrent stress tests or production
network benchmarks.

## 12. Documentation

See the docs directory:

- test_report.md
- mininet_validation.md
- failure_recovery_testing.md
- experimental_analysis.md

These reports contain previously recorded test results and
the environments in which they were collected.

## 13. Important Notes

- Mininet requires Linux; use the Ubuntu VM for SDN integration.
- Local UDP tests and benchmarks can be run on macOS.
- The SDN controller uses OS-Ken and OpenFlow 1.3.
- The controller listens on port 6653.
- DNS servers use UDP port 5353 in Mininet.
- Heartbeats use UDP port 9999.
- The heartbeat receiver must run while testing server health.
- Check the controller and heartbeat logs when debugging failures.

## Team Contributions

Member 1:
UDP client/server communication, caching, retries and validation.

Member 2:
Mininet topology, SDN controller, heartbeat monitoring,
round-robin traffic steering and server failover.

Member 3:
Testing, integration validation, performance evaluation
and technical documentation.
