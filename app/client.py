
# UDP client resolver with cache, retries and stats.
# Command line: python3 app/client.py video.lab [host:port]
# As a module: import client; client.resolve("video.lab")

import socket
import json
import time
import sys
import random
import os

# Cache: name -> (ip, expiry_time)
cache = {}
old_answers = {}

stats = {
    "cache_hits": 0,
    "network_lookups": 0,
    "successes": 0,
    "failures": 0,
    "retries": 0,
    "ignored_replies": 0
}

last_id = random.randint(1, 60000)

VALID_STATUSES = ("OK", "NOT_FOUND", "SERVFAIL")
MAX_TTL = 86400


# Read shared configuration.
def load_config():
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "..", "config", "config.json")

    with open(path) as f:
        return json.load(f)


config = load_config()


# Generate a unique query ID.
def new_query_id():
    global last_id
    last_id += 1
    return last_id


# Check cache for a valid entry.
def check_cache(name):
    if name not in cache:
        return None

    ip, expiry_time = cache[name]

    if time.time() < expiry_time:
        return ip

    del cache[name]
    return None


# Save successful answers in cache.
def save_to_cache(name, ip, ttl):
    cache[name] = (ip, time.time() + ttl)
    old_answers[name] = ip


# Select resolver address.
def get_server_addr():
    if config["baseline_mode"]:
        server = config["baseline_server"]
    else:
        server = config["virtual_resolver"]

    return (server["ip"], server["port"])


# Validate IPv4 address.
def is_valid_ip(ip):
    if not isinstance(ip, str):
        return False

    try:
        socket.inet_pton(socket.AF_INET, ip)
    except (OSError, ValueError):
        return False

    return True


# Validate TTL.
def is_valid_ttl(ttl):
    return (
        isinstance(ttl, int)
        and not isinstance(ttl, bool)
        and 0 <= ttl <= MAX_TTL
    )


# Validate server response.
def is_valid_reply(data, query_id, name):
    if not isinstance(data, dict):
        return False

    if data.get("id") != query_id:
        return False

    if data.get("name") != name:
        return False

    if data.get("status") not in VALID_STATUSES:
        return False

    if not is_valid_ttl(data.get("ttl")):
        return False

    if data["status"] == "OK":
        return is_valid_ip(data.get("ip"))

    return data.get("ip") is None


# Send one UDP query and wait for a valid response.
def send_query(name, server_addr):
    query_id = new_query_id()

    query = {
        "id": query_id,
        "name": name,
        "type": "A"
    }

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        sock.sendto(json.dumps(query).encode(), server_addr)

        deadline = time.time() + config["client"]["timeout"]
        reply = None

        while reply is None and time.time() < deadline:
            sock.settimeout(max(0.001, deadline - time.time()))

            try:
                packet, source = sock.recvfrom(4096)

            except socket.timeout:
                break

            except OSError:
                time.sleep(0.05)
                continue

            try:
                data = json.loads(packet.decode())

            except (ValueError, UnicodeDecodeError):
                stats["ignored_replies"] += 1
                continue

            if is_valid_reply(data, query_id, name):
                reply = data
            else:
                stats["ignored_replies"] += 1

        return reply

    finally:
        sock.close()


# Build result dictionary.
def make_result(name, ip, status, from_cache,
                start_time, attempts):

    latency_ms = (time.time() - start_time) * 1000

    return {
        "name": name,
        "ip": ip,
        "status": status,
        "from_cache": from_cache,
        "latency_ms": round(latency_ms, 3),
        "attempts": attempts
    }


# Main resolution function.
def resolve(name):
    start_time = time.time()

    # 1. Check cache first.
    cached_ip = check_cache(name)

    if cached_ip is not None:
        stats["cache_hits"] += 1

        return make_result(
            name, cached_ip, "OK",
            True, start_time, 0
        )

    # 2. Send network queries with retries.
    stats["network_lookups"] += 1

    server_addr = get_server_addr()
    max_retries = config["client"]["max_retries"]

    for attempt in range(1, max_retries + 1):

        if attempt > 1:
            stats["retries"] += 1

        reply = send_query(name, server_addr)

        if reply is not None:

            # Network failure reported by virtual resolver.
            if reply.get("status") == "SERVFAIL":
                stats["failures"] += 1

                return make_result(
                    name, None, "SERVFAIL",
                    False, start_time, attempt
                )

            # Valid DNS response.
            stats["successes"] += 1

            if reply.get("status") == "OK":
                save_to_cache(
                    name,
                    reply["ip"],
                    reply["ttl"]
                )

            return make_result(
                name,
                reply.get("ip"),
                reply.get("status"),
                False,
                start_time,
                attempt
            )

    # 3. All client attempts timed out.
    stats["failures"] += 1

    # 4. Use stale answer if available.
    if name in old_answers:
        return make_result(
            name,
            old_answers[name],
            "STALE",
            True,
            start_time,
            max_retries
        )

    return make_result(
        name,
        None,
        "FAILED",
        False,
        start_time,
        max_retries
    )


# Return statistics.
def get_stats():
    return dict(stats)


# Command-line interface.
def main():
    if len(sys.argv) < 2:
        print("usage: python3 client.py <name> [host:port]")
        sys.exit(1)

    if len(sys.argv) >= 3:
        host, port = sys.argv[2].split(":")

        config["baseline_mode"] = True
        config["baseline_server"] = {
            "ip": host,
            "port": int(port)
        }

    print(resolve(sys.argv[1]))
    print(get_stats())


if __name__ == "__main__":
    main()
