# UDP resolution server.
# Run: python3 app/server.py <server_id> <port> <records_file> [hb_ip hb_port]
import socket
import json
import time
import threading
import sys
import os

# Shared counter of answered queries (read by the heartbeat thread).
stats = {"queries_served": 0}


# Read the shared config file (one folder up from app/).
def load_config():
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "..", "config", "config.json")
    with open(path) as f:
        return json.load(f)


# Read the name -> {ip, ttl} table from a JSON file.
def load_records(path):
    with open(path) as f:
        return json.load(f)


# Check the packet is a dict with id (int), name (str) and type "A".
def is_valid_query(data):
    if not isinstance(data, dict):
        return False
    if not isinstance(data.get("id"), int) or isinstance(data.get("id"), bool):
        return False
    if not isinstance(data.get("name"), str):
        return False
    if data.get("type") != "A":
        return False
    return True


# Build the reply: OK with ip+ttl if the name is known, else NOT_FOUND.
def make_response(query, records):
    name = query["name"]
    if name in records:
        return {"id": query["id"], "name": name, "ip": records[name]["ip"],
                "ttl": records[name]["ttl"], "status": "OK"}
    return {"id": query["id"], "name": name, "ip": None,
            "ttl": 0, "status": "NOT_FOUND"}


# Background thread: every interval seconds tell the controller we are alive.
def send_heartbeats(server_id, hb_addr, interval):
    hb_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    while True:
        beat = {"server_id": server_id, "ts": time.time(),
                "queries_served": stats["queries_served"]}
        try:
            hb_sock.sendto(json.dumps(beat).encode(), hb_addr)
        except OSError:
            pass  # network not ready yet, just try again next time
        time.sleep(interval)


# Main loop: receive a packet, check it, answer it, count it.
def main():
    if len(sys.argv) < 4:
        print("usage: python3 server.py <server_id> <port> <records_file> [hb_ip hb_port]")
        sys.exit(1)
    server_id = sys.argv[1]
    port = int(sys.argv[2])
    records = load_records(sys.argv[3])
    config = load_config()
    hb = config["heartbeat"]
    hb_addr = (hb["ip"], hb["port"])
    if len(sys.argv) >= 6:  # optional override, used for local testing
        hb_addr = (sys.argv[4], int(sys.argv[5]))

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", port))
    thread = threading.Thread(target=send_heartbeats,
                              args=(server_id, hb_addr, hb["interval"]), daemon=True)
    thread.start()
    print("[%s] listening on UDP %d, %d records" % (server_id, port, len(records)), flush=True)

    while True:
        try:
            packet, client_addr = sock.recvfrom(4096)
        except OSError:
            continue  # e.g. Windows reports an ICMP error, keep going
        try:
            query = json.loads(packet.decode())
        except (ValueError, UnicodeDecodeError):
            print("[%s] ignored: bad JSON from %s" % (server_id, client_addr), flush=True)
            continue
        if not is_valid_query(query):
            print("[%s] ignored: invalid query from %s" % (server_id, client_addr), flush=True)
            continue
        reply = make_response(query, records)
        sock.sendto(json.dumps(reply).encode(), client_addr)
        stats["queries_served"] += 1
        print("[%s] query #%d %s -> %s (%s)" % (server_id, query["id"], query["name"],
              reply["ip"], reply["status"]), flush=True)


if __name__ == "__main__":
    main()
