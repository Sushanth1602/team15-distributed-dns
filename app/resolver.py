
import socket
import json
import os
import time
import itertools

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "..", "config", "config.json")
HEARTBEAT_FILE = "/tmp/team15_heartbeats.json"

with open(CONFIG_PATH) as f:
    config = json.load(f)

RESOLVER_IP = config["virtual_resolver"]["ip"]
RESOLVER_PORT = config["virtual_resolver"]["port"]

SERVER_IPS = [
    "10.0.0.11",
    "10.0.0.12",
    "10.0.0.13",
    "10.0.0.14",
    "10.0.0.15"
]

SERVER_PORTS = config["server_ports"]

TIMEOUT = config["client"]["timeout"]
MAX_MISSED = config["heartbeat"]["max_missed"]
INTERVAL = config["heartbeat"]["interval"]

round_robin = itertools.count()


# Find servers with fresh heartbeats.
def get_healthy_servers():
    try:
        with open(HEARTBEAT_FILE) as f:
            heartbeats = json.load(f)
    except (OSError, ValueError):
        return []

    now = time.time()
    healthy = []

    for ip, port in zip(SERVER_IPS, SERVER_PORTS):
        timestamp = heartbeats.get(ip)

        if timestamp is not None:
            if now - float(timestamp) <= MAX_MISSED * INTERVAL:
                healthy.append((ip, port))

    return healthy


# Send a query to one DNS server.
def query_server(query, server):
    ip, port = server

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(TIMEOUT)

    try:
        sock.sendto(
            json.dumps(query).encode(),
            (ip, port)
        )

        while True:
            data, address = sock.recvfrom(4096)
            reply = json.loads(data.decode())

            if (
                isinstance(reply, dict)
                and reply.get("id") == query["id"]
                and reply.get("name") == query["name"]
                and reply.get("status") in ("OK", "NOT_FOUND")
            ):
                return reply

    except (
        socket.timeout,
        OSError,
        ValueError,
        UnicodeDecodeError
    ):
        return None

    finally:
        sock.close()


# Send a response to the client.
def send_response(sock, reply, client_addr):
    sock.sendto(
        json.dumps(reply).encode(),
        client_addr
    )


# Main virtual DNS resolver.
def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((RESOLVER_IP, RESOLVER_PORT))

    print(
        f"Virtual DNS resolver listening on "
        f"{RESOLVER_IP}:{RESOLVER_PORT}",
        flush=True
    )

    while True:
        packet, client_addr = sock.recvfrom(4096)

        try:
            query = json.loads(packet.decode())

            if (
                not isinstance(query, dict)
                or not isinstance(query.get("id"), int)
                or isinstance(query.get("id"), bool)
                or not isinstance(query.get("name"), str)
                or query.get("type") != "A"
            ):
                continue

            healthy = get_healthy_servers()

            # No healthy servers: network failure.
            if not healthy:
                failure = {
                    "id": query["id"],
                    "name": query["name"],
                    "ip": None,
                    "ttl": 0,
                    "status": "SERVFAIL"
                }

                send_response(sock, failure, client_addr)

                print("No healthy DNS servers available",
                      flush=True)
                continue

            # Round-robin starting position.
            start = next(round_robin) % len(healthy)
            ordered = healthy[start:] + healthy[:start]

            all_not_found = True

            for server in ordered:
                reply = query_server(query, server)

                # A timeout means we cannot conclude NOT_FOUND.
                if reply is None:
                    all_not_found = False

                    print(
                        f"{server[0]} timed out; trying next server",
                        flush=True
                    )
                    continue

                # Successful resolution.
                if reply["status"] == "OK":
                    send_response(sock, reply, client_addr)

                    print(
                        f"{query['name']} resolved by {server[0]}",
                        flush=True
                    )
                    break

                # A genuine NOT_FOUND response.
                if reply["status"] == "NOT_FOUND":
                    print(
                        f"{server[0]} returned NOT_FOUND",
                        flush=True
                    )

            else:
                if all_not_found:
                    status = "NOT_FOUND"
                    print(
                        f"{query['name']} not found on healthy servers",
                        flush=True
                    )
                else:
                    status = "SERVFAIL"
                    print(
                        f"{query['name']} failed: server timeout",
                        flush=True
                    )

                response = {
                    "id": query["id"],
                    "name": query["name"],
                    "ip": None,
                    "ttl": 0,
                    "status": status
                }

                send_response(sock, response, client_addr)

        except (ValueError, UnicodeDecodeError):
            print("Invalid client query", flush=True)


if __name__ == "__main__":
    main()
