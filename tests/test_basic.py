# Basic local tests (127.0.0.1 only, no Mininet).
# Run: python3 tests/test_basic.py
import socket
import json
import subprocess
import threading
import time
import sys
import os

here = os.path.dirname(os.path.abspath(__file__))
root = os.path.join(here, "..")
sys.path.insert(0, os.path.join(root, "app"))
import client

SERVER_PORT = 5301
HB_PORT = 9999
FAKE_PORT = 5400
DEAD_PORT = 5999  # nothing listens here
BAD_PORT = 5401  # fake server for the bad-reply test
ONLY_BAD_PORT = 5402  # fake server that only sends bad replies
results = []


# Print PASS/FAIL with what we expected and what we got.
def check(label, ok, expected, got):
    status = "PASS" if ok else "FAIL"
    results.append(ok)
    print("[%s] %s\n       expected: %s\n       got:      %s" % (status, label, expected, got))


# Point the client at one local server and wipe its cache and counters.
def reset_client(port):
    client.cache.clear()
    client.old_answers.clear()
    for key in client.stats:
        client.stats[key] = 0
    client.config["baseline_mode"] = True
    client.config["baseline_server"] = {"ip": "127.0.0.1", "port": port}


# Start the real server.py as a subprocess, heartbeats go to our local listener.
def start_server():
    cmd = [sys.executable, os.path.join(root, "app", "server.py"), "s1", str(SERVER_PORT),
           os.path.join(root, "app", "records", "server1.json"), "127.0.0.1", str(HB_PORT)]
    process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL)
    time.sleep(0.7)
    return process


# Fake server: for each query send a wrong-id reply, then the right reply twice.
def fake_server(sock):
    packet, addr = sock.recvfrom(4096)
    query = json.loads(packet.decode())
    wrong = {"id": query["id"] + 999, "name": query["name"], "ip": "9.9.9.9", "ttl": 30, "status": "OK"}
    right = {"id": query["id"], "name": query["name"], "ip": "1.2.3.4", "ttl": 30, "status": "OK"}
    sock.sendto(json.dumps(wrong).encode(), addr)
    sock.sendto(json.dumps(right).encode(), addr)
    sock.sendto(json.dumps(right).encode(), addr)  # duplicate


# Fake server for the validation test: for ONE query send many bad replies, then one good reply.
def bad_then_good_server(sock):
    packet, addr = sock.recvfrom(4096)
    query = json.loads(packet.decode())
    qid, name = query["id"], query["name"]
    good = {"id": qid, "name": name, "ip": "1.2.3.4", "ttl": 30, "status": "OK"}
    bad_replies = [
        dict(good, name="other.lab"),      # name does not match the query
        dict(good, status="MAYBE"),        # status not allowed
        dict(good, status="ok"),           # wrong case, not allowed
        dict(good, ip="999.1.1.1"),        # not a real IPv4
        dict(good, ip="10.0.1"),           # too few parts
        dict(good, ip=None),               # OK must have an ip
        dict(good, ip=12345),              # ip is not text
        dict(good, ttl=-5),                # negative ttl
        dict(good, ttl="30"),              # ttl is text
        dict(good, ttl=99999999),          # ttl too big
        dict(good, ttl=True),              # bool is not a number here
        dict(good, status="NOT_FOUND"),    # NOT_FOUND must have ip = null
        ["not", "a", "dict"],              # valid JSON but not an object
    ]
    for reply in bad_replies:
        sock.sendto(json.dumps(reply).encode(), addr)
    sock.sendto(b"\xff\xfe not json", addr)  # not even JSON
    sock.sendto(json.dumps(good).encode(), addr)
    return len(bad_replies) + 1


# Fake server that only ever sends a bad reply (wrong name), once per query.
def only_bad_server(sock, rounds):
    for i in range(rounds):
        packet, addr = sock.recvfrom(4096)
        query = json.loads(packet.decode())
        bad = {"id": query["id"], "name": "other.lab", "ip": "1.2.3.4", "ttl": 30, "status": "OK"}
        sock.sendto(json.dumps(bad).encode(), addr)


def main():
    # Heartbeat listener must exist before the server starts.
    hb_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    hb_sock.bind(("127.0.0.1", HB_PORT))
    hb_sock.settimeout(3)
    server = start_server()

    # a) known name
    reset_client(SERVER_PORT)
    r = client.resolve("video.lab")
    check("a) known name resolves", r["ip"] == "10.0.1.11" and r["status"] == "OK",
          "ip=10.0.1.11 status=OK", "ip=%s status=%s" % (r["ip"], r["status"]))

    # b) unknown name
    r = client.resolve("nothere.lab")
    check("b) unknown name -> NOT_FOUND", r["status"] == "NOT_FOUND" and r["ip"] is None,
          "ip=None status=NOT_FOUND", "ip=%s status=%s" % (r["ip"], r["status"]))

    # c) second lookup is a cache hit, no packet (network_lookups does not grow)
    before = client.get_stats()
    r = client.resolve("video.lab")
    after = client.get_stats()
    ok = (r["from_cache"] and after["cache_hits"] == before["cache_hits"] + 1
          and after["network_lookups"] == before["network_lookups"])
    check("c) 2nd lookup is cache hit, no packet", ok,
          "from_cache=True, cache_hits +1, network_lookups unchanged",
          "from_cache=%s, cache_hits %d->%d, network_lookups %d->%d" % (
              r["from_cache"], before["cache_hits"], after["cache_hits"],
              before["network_lookups"], after["network_lookups"]))

    # d) web.lab has TTL 3: hit at first, new network lookup after 3+ seconds
    reset_client(SERVER_PORT)
    client.resolve("web.lab")
    hit = client.resolve("web.lab")
    time.sleep(3.3)
    again = client.resolve("web.lab")
    ok = hit["from_cache"] and not again["from_cache"] and client.get_stats()["network_lookups"] == 2
    check("d) short TTL expires, new lookup sent", ok,
          "before expiry from_cache=True; after expiry from_cache=False, network_lookups=2",
          "before=%s after=%s network_lookups=%d" % (hit["from_cache"], again["from_cache"],
                                                    client.get_stats()["network_lookups"]))

    # f) garbage packet is ignored, next valid query still answered
    junk = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    junk.sendto(b"\xff\xfe not json", ("127.0.0.1", SERVER_PORT))
    junk.close()
    reset_client(SERVER_PORT)
    r = client.resolve("mail.lab")
    check("f) malformed packet ignored, server still works", r["ip"] == "10.0.1.13",
          "ip=10.0.1.13", "ip=%s" % r["ip"])

    # h) heartbeat arrives with the right fields
    try:
        beat = json.loads(hb_sock.recvfrom(4096)[0].decode())
    except socket.timeout:
        beat = {}
    ok = beat.get("server_id") == "s1" and "ts" in beat and "queries_served" in beat
    check("h) heartbeat received", ok, "keys server_id='s1', ts, queries_served", str(beat))

    # e) server down: 3 attempts, 2 retries, then stale or clean failure
    server.terminate()
    server.wait()
    reset_client(SERVER_PORT)
    r = client.resolve("video.lab")  # nothing cached yet -> clean failure
    s = client.get_stats()
    ok = r["status"] == "FAILED" and r["attempts"] == 3 and s["retries"] == 2 and s["failures"] == 1
    check("e1) server down -> retries then clean failure", ok,
          "status=FAILED attempts=3 retries=2 failures=1",
          "status=%s attempts=%d retries=%d failures=%d" % (r["status"], r["attempts"], s["retries"], s["failures"]))
    client.save_to_cache("video.lab", "10.0.1.11", 0)  # already expired
    r = client.resolve("video.lab")
    check("e2) server down + old cache -> stale answer", r["status"] == "STALE" and r["ip"] == "10.0.1.11",
          "status=STALE ip=10.0.1.11", "status=%s ip=%s" % (r["status"], r["ip"]))

    # g) wrong-id reply and duplicate reply are ignored
    fake_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    fake_sock.bind(("127.0.0.1", FAKE_PORT))
    threading.Thread(target=fake_server, args=(fake_sock,), daemon=True).start()
    reset_client(FAKE_PORT)
    r = client.resolve("anything.lab")
    check("g) wrong-id and duplicate replies ignored", r["ip"] == "1.2.3.4" and r["attempts"] == 1,
          "ip=1.2.3.4 attempts=1 (9.9.9.9 ignored)", "ip=%s attempts=%d" % (r["ip"], r["attempts"]))
    fake_sock.close()


    # i) malformed or mismatched replies are ignored, only the good one is accepted and cached
    bad_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    bad_sock.bind(("127.0.0.1", BAD_PORT))
    threading.Thread(target=bad_then_good_server, args=(bad_sock,), daemon=True).start()
    reset_client(BAD_PORT)
    r = client.resolve("check.lab")
    s = client.get_stats()
    ok = (r["ip"] == "1.2.3.4" and r["status"] == "OK" and r["attempts"] == 1
          and s["ignored_replies"] == 14 and client.cache["check.lab"][0] == "1.2.3.4")
    check("i) 14 bad replies ignored, good one accepted + cached", ok,
          "ip=1.2.3.4 attempts=1 ignored_replies=14 cached ip=1.2.3.4",
          "ip=%s attempts=%d ignored_replies=%d cached=%s" % (
              r["ip"], r["attempts"], s["ignored_replies"], client.cache.get("check.lab")))
    bad_sock.close()

    # j) only bad replies ever arrive: nothing is cached, lookup ends as FAILED after all attempts
    only_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    only_sock.bind(("127.0.0.1", ONLY_BAD_PORT))
    threading.Thread(target=only_bad_server, args=(only_sock, 3), daemon=True).start()
    reset_client(ONLY_BAD_PORT)
    r = client.resolve("check.lab")
    ok = r["status"] == "FAILED" and r["attempts"] == 3 and "check.lab" not in client.cache
    check("j) only bad replies -> FAILED, nothing cached", ok,
          "status=FAILED attempts=3 cache empty",
          "status=%s attempts=%d cached=%s" % (r["status"], r["attempts"], client.cache.get("check.lab")))
    only_sock.close()

    print("\n%d of %d tests passed" % (results.count(True), len(results)))
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
