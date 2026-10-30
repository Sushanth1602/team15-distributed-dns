# UDP client resolver with cache, retries and stats.
# Command line: python3 app/client.py video.lab [host:port]
# As a module:  import client; client.resolve("video.lab")
import socket
import json
import time
import sys
import random
import os

# cache: name -> (ip, expiry_time). old_answers keeps the last ip for stale fallback.
cache = {}
old_answers = {}
stats = {"cache_hits": 0, "network_lookups": 0, "successes": 0, "failures": 0, "retries": 0}
last_id = random.randint(1, 60000)  # query ids count up from a random start


# Read the shared config file (one folder up from app/).
def load_config():
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "..", "config", "config.json")
    with open(path) as f:
        return json.load(f)


config = load_config()


# Give back a new query id (counter, so no id repeats).
def new_query_id():
    global last_id
    last_id = last_id + 1
    return last_id


# Return the cached ip if it is still fresh. Delete the entry if it expired.
def check_cache(name):
    if name not in cache:
        return None
    ip, expiry_time = cache[name]
    if time.time() < expiry_time:
        return ip
    del cache[name]
    return None


# Remember an answer for ttl seconds (and keep it as a stale backup).
def save_to_cache(name, ip, ttl):
    cache[name] = (ip, time.time() + ttl)
    old_answers[name] = ip


# Pick where to send queries: the virtual resolver, or the fixed server in baseline mode.
def get_server_addr():
    if config["baseline_mode"]:
        server = config["baseline_server"]
    else:
        server = config["virtual_resolver"]
    return (server["ip"], server["port"])


# One attempt: send the query, wait up to timeout for a reply with the SAME id.
# Replies with other ids (old, unknown, duplicate) are ignored. Returns reply or None.
def send_query(name, server_addr):
    query_id = new_query_id()
    query = {"id": query_id, "name": name, "type": "A"}
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # new socket, no connect()
    sock.sendto(json.dumps(query).encode(), server_addr)
    deadline = time.time() + config["client"]["timeout"]
    reply = None
    while reply is None and time.time() < deadline:
        sock.settimeout(deadline - time.time())
        try:
            packet, source = sock.recvfrom(4096)  # source IP is NOT checked
        except socket.timeout:
            break
        except OSError:
            time.sleep(0.05)  # e.g. Windows "port unreachable" error, keep waiting
            continue
        try:
            data = json.loads(packet.decode())
        except (ValueError, UnicodeDecodeError):
            continue
        if isinstance(data, dict) and data.get("id") == query_id:
            reply = data
    sock.close()
    return reply


# Build the small result dict that is returned to the caller.
def make_result(name, ip, status, from_cache, start_time, attempts):
    latency_ms = (time.time() - start_time) * 1000
    return {"name": name, "ip": ip, "status": status, "from_cache": from_cache,
            "latency_ms": round(latency_ms, 3), "attempts": attempts}


# Main function: cache first, then network with retries, then stale fallback.
def resolve(name):
    start_time = time.time()
    cached_ip = check_cache(name)
    if cached_ip is not None:
        stats["cache_hits"] += 1  # cache hit: no packet is sent
        return make_result(name, cached_ip, "OK", True, start_time, 0)

    stats["network_lookups"] += 1
    server_addr = get_server_addr()
    for attempt in range(1, config["client"]["max_retries"] + 1):
        if attempt > 1:
            stats["retries"] += 1
        reply = send_query(name, server_addr)
        if reply is not None:
            stats["successes"] += 1
            if reply.get("status") == "OK":  # only cache OK answers
                save_to_cache(name, reply["ip"], reply["ttl"])
            return make_result(name, reply.get("ip"), reply.get("status"),
                               False, start_time, attempt)

    stats["failures"] += 1  # every attempt timed out
    attempts = config["client"]["max_retries"]
    if name in old_answers:
        return make_result(name, old_answers[name], "STALE", True, start_time, attempts)
    return make_result(name, None, "FAILED", False, start_time, attempts)


# Return a copy of the counters.
def get_stats():
    return dict(stats)


# Command line: resolve one name and print the result and stats.
def main():
    if len(sys.argv) < 2:
        print("usage: python3 client.py <name> [host:port]")
        sys.exit(1)
    if len(sys.argv) >= 3:  # fixed server (baseline mode), handy for local testing
        host, port = sys.argv[2].split(":")
        config["baseline_mode"] = True
        config["baseline_server"] = {"ip": host, "port": int(port)}
    print(resolve(sys.argv[1]))
    print(get_stats())


if __name__ == "__main__":
    main()
