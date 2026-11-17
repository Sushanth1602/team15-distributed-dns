
import json
import socket
import sys
import tempfile
import threading
import time
import unittest
import itertools
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import resolver


class FakeDNSServer:
    def __init__(self, status="OK"):
        self.status = status
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 0))
        self.port = self.sock.getsockname()[1]
        self.running = True
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        while self.running:
            try:
                data, address = self.sock.recvfrom(4096)
                query = json.loads(data.decode())

                reply = {
                    "id": query["id"],
                    "name": query["name"],
                    "ip": "192.0.2.10" if self.status == "OK" else None,
                    "ttl": 30 if self.status == "OK" else 0,
                    "status": self.status
                }

                self.sock.sendto(json.dumps(reply).encode(), address)

            except OSError:
                break

    def close(self):
        if self.running:
            self.running = False
            self.sock.close()
            self.thread.join(timeout=1)


class ResolverIntegrationTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.heartbeat_file = Path(self.temp.name) / "heartbeats.json"

        self.old = {
            "heartbeat": resolver.HEARTBEAT_FILE,
            "ips": resolver.SERVER_IPS,
            "ports": resolver.SERVER_PORTS,
            "timeout": resolver.TIMEOUT,
            "counter": resolver.round_robin
        }

        resolver.HEARTBEAT_FILE = str(self.heartbeat_file)
        resolver.TIMEOUT = 0.2
        resolver.MAX_MISSED = 3
        resolver.INTERVAL = 1

        self.servers = [FakeDNSServer() for _ in range(3)]

        resolver.SERVER_IPS = ["127.0.0.1"] * 3
        resolver.SERVER_PORTS = [s.port for s in self.servers]
        resolver.round_robin = itertools.count()

        self.query = {
            "id": 123,
            "name": "video.lab",
            "type": "A"
        }

    def tearDown(self):
        for server in self.servers:
            server.close()

        resolver.HEARTBEAT_FILE = self.old["heartbeat"]
        resolver.SERVER_IPS = self.old["ips"]
        resolver.SERVER_PORTS = self.old["ports"]
        resolver.TIMEOUT = self.old["timeout"]
        resolver.round_robin = self.old["counter"]

        self.temp.cleanup()

    def write_heartbeats(self, indexes):
        data = {
            resolver.SERVER_IPS[i]: time.time()
            for i in indexes
        }
        self.heartbeat_file.write_text(json.dumps(data))

    def test_01_healthy_resolution(self):
        self.write_heartbeats([0, 1, 2])

        result = resolver.handle_query(self.query)

        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["ip"], "192.0.2.10")

    def test_02_domain_not_found(self):
        for server in self.servers:
            server.status = "NOT_FOUND"

        self.write_heartbeats([0, 1, 2])

        result = resolver.handle_query(self.query)

        self.assertEqual(result["status"], "NOT_FOUND")

    def test_03_no_healthy_servers(self):
        self.write_heartbeats([])

        result = resolver.handle_query(self.query)

        self.assertEqual(result["status"], "SERVFAIL")

    def test_04_failed_server_fallback(self):
        self.servers[0].close()
        self.write_heartbeats([0, 1, 2])

        result = resolver.handle_query(self.query)

        self.assertEqual(result["status"], "OK")

    def test_05_all_servers_timeout(self):
        for server in self.servers:
            server.close()

        self.write_heartbeats([0, 1, 2])

        result = resolver.handle_query(self.query)

        self.assertEqual(result["status"], "SERVFAIL")

    def test_06_server_recovery(self):
        for server in self.servers:
            server.close()

        self.write_heartbeats([0, 1, 2])
        failed_result = resolver.handle_query(self.query)
        self.assertEqual(failed_result["status"], "SERVFAIL")

        recovered_server = FakeDNSServer()
        self.servers.append(recovered_server)

        resolver.SERVER_IPS = ["127.0.0.1"]
        resolver.SERVER_PORTS = [recovered_server.port]
        resolver.round_robin = itertools.count()

        self.write_heartbeats([0])

        recovered_result = resolver.handle_query(self.query)

        self.assertEqual(recovered_result["status"], "OK")
        self.assertEqual(recovered_result["ip"], "192.0.2.10")


if __name__ == "__main__":
    unittest.main(verbosity=2)
