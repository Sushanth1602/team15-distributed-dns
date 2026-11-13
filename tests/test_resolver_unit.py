
import sys
import json
import time
import socket
import threading
import tempfile
import unittest
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "app")
)

import resolver


class ResolverUnitTests(unittest.TestCase):

    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(
            mode="w",
            delete=False
        )
        self.heartbeat_path = self.temp_file.name
        self.temp_file.close()

        resolver.HEARTBEAT_FILE = self.heartbeat_path
        resolver.SERVER_IPS = [
            "127.0.0.1",
            "127.0.0.2",
            "127.0.0.3"
        ]
        resolver.SERVER_PORTS = [5301, 5302, 5303]

    def tearDown(self):
        Path(self.heartbeat_path).unlink(missing_ok=True)

    def write_heartbeats(self, data):
        with open(self.heartbeat_path, "w") as f:
            json.dump(data, f)

    def test_healthy_server_detection(self):
        now = time.time()

        self.write_heartbeats({
            "127.0.0.1": now,
            "127.0.0.2": now,
            "127.0.0.3": now - 100
        })

        healthy = resolver.get_healthy_servers()

        self.assertEqual(
            healthy,
            [
                ("127.0.0.1", 5301),
                ("127.0.0.2", 5302)
            ]
        )

    def test_no_heartbeat_means_no_healthy_servers(self):
        self.write_heartbeats({})

        healthy = resolver.get_healthy_servers()

        self.assertEqual(healthy, [])

    def test_stale_heartbeat_is_rejected(self):
        self.write_heartbeats({
            "127.0.0.1": time.time() - 100
        })

        healthy = resolver.get_healthy_servers()

        self.assertEqual(healthy, [])

    def test_query_server_accepts_valid_response(self):
        server = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM
        )
        server.bind(("127.0.0.1", 0))

        port = server.getsockname()[1]

        def respond():
            data, address = server.recvfrom(4096)
            query = json.loads(data.decode())

            response = {
                "id": query["id"],
                "name": query["name"],
                "ip": "10.0.0.11",
                "ttl": 30,
                "status": "OK"
            }

            server.sendto(
                json.dumps(response).encode(),
                address
            )

        thread = threading.Thread(
            target=respond,
            daemon=True
        )
        thread.start()

        query = {
            "id": 123,
            "name": "video.lab",
            "type": "A"
        }

        try:
            result = resolver.query_server(
                query,
                ("127.0.0.1", port)
            )

            self.assertIsNotNone(result)
            self.assertEqual(result["status"], "OK")
            self.assertEqual(result["ip"], "10.0.0.11")

        finally:
            server.close()

    def test_query_server_timeout(self):
        result = resolver.query_server(
            {
                "id": 456,
                "name": "video.lab",
                "type": "A"
            },
            ("127.0.0.1", 59999)
        )

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
