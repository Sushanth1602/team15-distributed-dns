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
stats = {"cache_hits": 0, "network_lookups": 0, "successes": 0, "failures": 0, "retries": 0,
         "ignored_replies": 0}  # ignored_replies = packets we received but did not accept
last_id = random.randint(1, 60000)  # query ids count up from a random start

VALID_STATUSES = ("OK", "NOT_FOUND")  # the only status values the spec allows
MAX_TTL = 86400  # biggest TTL we accept (1 day); anything larger is treated as bad


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


# True if ip is text in proper dotted form like 10.0.1.11 (4 numbers, each 0-255).
def is_valid_ip(ip):
    if not isinstance(ip, str):
        return False
    try:
        socket.inet_pton(socket.AF_INET, ip)  # raises an error for anything not a real IPv4
    except (OSError, ValueError):
        return False
    return True


# True if ttl is a whole number from 0 to MAX_TTL (True/False are not accepted).
def is_valid_ttl(ttl):
    if not isinstance(ttl, int) or isinstance(ttl, bool):
        return False
    return 0 <= ttl <= MAX_TTL


# Check a reply before we trust it: same id and name as our query, known status,
# and a sensible ip and ttl. Anything else is rejected.
def is_valid_reply(data, query_id, name):
    if not isinstance(data, dict):
        return False
    if data.get("id") != query_id:  # reply to some other query
        return False
    if data.get("name") != name:  # reply is about a different name
        return False
    if data.get("status") not in VALID_STATUSES:
        return False
    if not is_valid_ttl(data.get("ttl")):
        return False
    if data["status"] == "OK":
        return is_valid_ip(data.get("ip"))  # OK must carry a real ip
    return data.get("ip") is None  # NOT_FOUND must have ip = null


# One attempt: send the query, wait up to timeout for a VALID reply to this query.
# Replies that are malformed, mismatched, old or duplicate are ignored. Returns reply or None.
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
            stats["ignored_replies"] += 1  # not JSON at all
            continue
        if is_valid_reply(data, query_id, name):
            reply = data
        else:
            stats["ignored_replies"] += 1  # keep waiting for a good reply until timeout
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
