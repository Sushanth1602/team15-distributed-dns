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

```text
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
```

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

```bash
git clone https://github.com/Sushanth1602/team15-distributed-dns.git
cd team15-distributed-dns
```

## 2. Install System Dependencies

```bash
sudo apt update
sudo apt install -y git python3 python3-pip python3-venv
sudo apt install -y mininet openvswitch-switch
sudo systemctl start openvswitch-switch
```

## 3. Create the Python Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install pytest pandas matplotlib os-ken
python -c "import os_ken; print('OS-Ken installed')"
```

If OS-Ken is installed in a different virtual environment, activate that
environment before starting the network, or set `OSKEN_PYTHON` to the
full path of the Python executable that has OS-Ken installed.

## 4. Run Automated Tests

Run the basic UDP tests:

```bash
python3 tests/test_basic.py
```

Run the cache, resolver integration and resolver unit tests:

```bash
python3 -m pytest tests/test_cache.py tests/test_resolver_integration.py tests/test_resolver_unit.py -v
```

## 5. Start the SDN Controller and Mininet

Run this from a normal Ubuntu terminal in the repository directory.
The script starts the OS-Ken controller, waits briefly for it to start,
and then launches the Mininet topology. It accepts 1, 3 or 5 DNS servers.

Before starting, clear any stale Mininet state and ensure the startup script is executable:

```bash
sudo mn -c
chmod +x scripts/start_network.sh
```

For five DNS servers:

```bash
source .venv/bin/activate
./scripts/start_network.sh 5
```

For one or three DNS servers, use:

```bash
./scripts/start_network.sh 1
./scripts/start_network.sh 3
```

If OS-Ken is installed in a separate environment, provide its Python
executable (replace the example path with the actual path):

```bash
OSKEN_PYTHON=/path/to/osken-env/bin/python ./scripts/start_network.sh 5
```

The script runs the controller in the background and keeps it running
while Mininet is active. The Mininet CLI appears in this terminal.
When you exit the Mininet CLI, the script stops the controller.

Controller output is written to `logs/controller.log`. To inspect it
from another terminal:

```bash
tail -f logs/controller.log
```

## 6. Verify the Mininet Topology

At the Mininet prompt:

```text
pingall
```

All hosts should be reachable. The topology supports 1, 3 or 5 DNS
servers. Keep the terminal running at the Mininet prompt.

## 7. Start the Heartbeat Receiver

After the topology has started, open a second Ubuntu terminal in the
repository directory:

```bash
python3 scripts/heartbeat_receiver.py
```

The monitor host uses IP address `10.0.0.100` and listens on UDP port
`9999`. Keep this terminal running while testing server health.

## 8. Start DNS Servers

At the Mininet prompt, start the servers that exist in the selected
topology. For a five-server topology:

```text
dns1 python3 app/server.py s1 5353 app/records/server1.json &
dns2 python3 app/server.py s2 5353 app/records/server2.json &
dns3 python3 app/server.py s3 5353 app/records/server3.json &
dns4 python3 app/server.py s4 5353 app/records/server4.json &
dns5 python3 app/server.py s5 5353 app/records/server5.json &
```

For a one- or three-server topology, start only the corresponding
number of DNS servers. Wait for heartbeat messages and for the
controller to learn the DNS server locations.

## 9. Test DNS Resolution

At the Mininet prompt:

```text
client python3 app/client.py video.lab
client python3 app/client.py unknown.lab
```

Expected results:

- `video.lab` returns status `OK`.
- `unknown.lab` returns status `NOT_FOUND`.

Repeat a successful query before TTL expiry to test client caching.

In the Mininet integration, the SDN controller intercepts queries
addressed to the virtual DNS IP and redirects them to DNS servers.
The application-level resolver module is also used by local tests
and performance experiments.

## 10. Test Server Failure and Recovery

Stop DNS3 at the Mininet prompt:

```text
dns3 pkill -f app/server.py
```

Wait longer than the heartbeat timeout, then issue a fresh query:

```text
client python3 app/client.py video.lab
```

The controller should detect DNS3 failure and select another healthy
DNS server.

Restart DNS3:

```text
dns3 python3 app/server.py s3 5353 app/records/server3.json &
```

Wait for fresh heartbeats and verify recovery in the controller log.
Use fresh queries so an earlier client cache entry does not hide
the network behavior.

## 11. Performance Evaluation

Run the localhost performance experiments:

```bash
python3 experiments/load_generator.py --servers 1 --queries 100
python3 experiments/load_generator.py --servers 3 --queries 100
python3 experiments/load_generator.py --servers 5 --queries 100
```

Run a missing-domain experiment:

```bash
python3 experiments/load_generator.py --servers 3 --queries 100 --scenario missing
```

Generate graphs:

```bash
python3 experiments/generate_graphs.py
```

Results are stored in `results/raw/` and `results/`. These localhost
experiments are application-level sequential measurements. They are
not concurrent stress tests or production network benchmarks.

## 12. Documentation

See the `docs/` directory:

- `test_report.md`
- `mininet_validation.md`
- `failure_recovery_testing.md`
- `experimental_analysis.md`

These reports contain previously recorded test results and the
environments in which they were collected.

## 13. Important Notes

- Mininet requires Linux; use the Ubuntu VM for SDN integration.
- Local UDP tests and benchmarks can be run on macOS.
- The SDN controller uses OS-Ken and OpenFlow 1.3.
- The controller listens on OpenFlow TCP port `6653`.
- DNS servers use UDP port `5353` in Mininet.
- Heartbeats use UDP port `9999`.
- Keep the heartbeat receiver running while testing server health.
- Check `logs/controller.log` and the heartbeat receiver terminal
  when debugging failures.

## Team Contributions

**Member 1:** UDP client/server communication, caching, retries and validation.

**Member 2:** Mininet topology, SDN controller, heartbeat monitoring,
round-robin traffic steering and server failover.

**Member 3:** Testing, integration validation, performance evaluation
and technical documentation.
