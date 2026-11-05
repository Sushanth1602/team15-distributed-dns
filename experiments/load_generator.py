
import sys
import csv
import json
import time
import argparse
import statistics
import socket
import subprocess
import threading
import tempfile
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app"
CONFIG_FILE = ROOT / "config" / "config.json"

sys.path.insert(0, str(APP_DIR))
import resolver

LOCAL_IP = "127.0.0.1"
HEARTBEAT_PORT = 9999

RESULTS_DIR = ROOT / "results"
RAW_DIR = RESULTS_DIR / "raw"
SUMMARY_FILE = RESULTS_DIR / "summary.csv"


class HeartbeatReceiver:
    def __init__(self, heartbeat_file):
        self.heartbeat_file = Path(heartbeat_file)
        self.running = False
        self.sock = None
        self.thread = None
        self.heartbeats = {}
        self.lock = threading.Lock()

    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((LOCAL_IP, HEARTBEAT_PORT))
        self.sock.settimeout(1)

        self.running = True
        self.thread = threading.Thread(
            target=self.receive,
            daemon=True
        )
        self.thread.start()

    def receive(self):
        while self.running:
            try:
                data, address = self.sock.recvfrom(4096)
                packet = json.loads(data.decode())

                timestamp = packet.get("ts", time.time())

                with self.lock:
                    self.heartbeats[address[0]] = timestamp

                    temp_file = self.heartbeat_file.with_suffix(".tmp")
                    temp_file.write_text(json.dumps(self.heartbeats))
                    temp_file.replace(self.heartbeat_file)

            except socket.timeout:
                continue
            except (OSError, ValueError, json.JSONDecodeError):
                if self.running:
                    continue

    def stop(self):
        self.running = False

        if self.sock:
            self.sock.close()

        if self.thread:
            self.thread.join(timeout=2)


def load_config():
    with open(CONFIG_FILE, "r") as file:
        return json.load(file)


def start_local_servers(config, server_count):
    processes = []
    ports = config["server_ports"][:server_count]

    for index, port in enumerate(ports, start=1):
        server_id = f"s{index}"
        records_file = APP_DIR / "records" / f"server{index}.json"

        command = [
            sys.executable,
            str(APP_DIR / "server.py"),
            server_id,
            str(port),
            str(records_file),
            LOCAL_IP,
            str(HEARTBEAT_PORT),
        ]

        process = subprocess.Popen(
            command,
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        processes.append(process)

    return processes, ports


def stop_local_servers(processes):
    for process in processes:
        if process.poll() is None:
            process.terminate()

    for process in processes:
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def wait_for_healthy_servers(expected_count, processes, timeout=10):
    start = time.time()

    while time.time() - start < timeout:
        if any(process.poll() is not None for process in processes):
            return False

        healthy = resolver.get_healthy_servers()

        if len(healthy) >= expected_count:
            return True

        time.sleep(0.25)

    return False


def run_experiment(query_count, domain, scenario):
    rows = []
    latencies = []

    for number in range(1, query_count + 1):
        query = {
            "id": number,
            "name": domain,
            "type": "A",
        }

        start = time.perf_counter()
        response = resolver.handle_query(query)
        elapsed_ms = (time.perf_counter() - start) * 1000

        status = response.get("status", "ERROR") if response else "ERROR"
        answer_ip = response.get("ip") if response else None

        latencies.append(elapsed_ms)

        rows.append({
            "query_number": number,
            "domain": domain,
            "status": status,
            "answer_ip": answer_ip,
            "latency_ms": round(elapsed_ms, 4),
            "scenario": scenario,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    successful = sum(row["status"] == "OK" for row in rows)
    not_found = sum(row["status"] == "NOT_FOUND" for row in rows)
    failed = query_count - successful - not_found

    total_time = sum(latencies) / 1000

    summary = {
        "scenario": scenario,
        "queries": query_count,
        "successful": successful,
        "not_found": not_found,
        "failed": failed,
        "success_rate_percent": round(
            successful / query_count * 100, 2
        ),
        "average_latency_ms": round(
            statistics.mean(latencies), 4
        ),
        "median_latency_ms": round(
            statistics.median(latencies), 4
        ),
        "min_latency_ms": round(min(latencies), 4),
        "max_latency_ms": round(max(latencies), 4),
        "p95_latency_ms": round(
            sorted(latencies)[min(
                len(latencies) - 1,
                int(len(latencies) * 0.95)
            )],
            4
        ),
        "total_time_seconds": round(total_time, 6),
        "throughput_qps": round(
            query_count / total_time, 2
        ) if total_time > 0 else 0,
    }

    return rows, summary


def save_results(rows, summary, server_count):
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_file = RAW_DIR / f"run_{server_count}servers_{timestamp}.csv"

    if rows:
        with open(raw_file, "w", newline="") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=list(rows[0].keys())
            )
            writer.writeheader()
            writer.writerows(rows)

    summary["servers"] = server_count
    summary["run_timestamp"] = timestamp

    existing = []

    if SUMMARY_FILE.exists():
        with open(SUMMARY_FILE, "r", newline="") as file:
            existing = list(csv.DictReader(file))

    fieldnames = list(dict.fromkeys(
        key
        for row in existing + [summary]
        for key in row.keys()
    ))

    with open(SUMMARY_FILE, "w", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(existing)
        writer.writerow(summary)

    print(f"\nRaw results saved: {raw_file}")
    print(f"Summary saved: {SUMMARY_FILE}")


def main():
    parser = argparse.ArgumentParser(
        description="Distributed DNS performance load generator"
    )

    parser.add_argument("--queries", type=int, default=100)
    parser.add_argument("--domain", default="video.lab")
    parser.add_argument(
        "--scenario",
        choices=["normal", "missing"],
        default="normal"
    )
    parser.add_argument(
        "--servers",
        type=int,
        choices=[1, 3, 5],
        default=1
    )

    args = parser.parse_args()

    if args.queries < 1:
        parser.error("--queries must be at least 1")

    config = load_config()

    if args.servers > len(config["server_ports"]):
        parser.error("Not enough server ports in config.json")

    domain = (
        "missing.lab"
        if args.scenario == "missing"
        else args.domain
    )

    old_ips = resolver.SERVER_IPS
    old_ports = resolver.SERVER_PORTS
    old_heartbeat_file = resolver.HEARTBEAT_FILE

    processes = []
    receiver = None

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            heartbeat_file = Path(temp_dir) / "heartbeats.json"
            heartbeat_file.write_text("{}")

            ports = config["server_ports"][:args.servers]

            # Local test setup: same IP, different UDP ports.
            resolver.SERVER_IPS = [LOCAL_IP] * args.servers
            resolver.SERVER_PORTS = ports
            resolver.HEARTBEAT_FILE = str(heartbeat_file)

            receiver = HeartbeatReceiver(heartbeat_file)
            receiver.start()

            processes, ports = start_local_servers(
                config,
                args.servers
            )

            print(f"\nStarted {args.servers} DNS server(s).")
            print(f"Server IP: {LOCAL_IP}")
            print(f"Server ports: {ports}")
            print("Waiting for heartbeats...")

            if not wait_for_healthy_servers(
                args.servers,
                processes
            ):
                raise RuntimeError(
                    "Expected servers did not become healthy. "
                    "Check server startup and heartbeat configuration."
                )

            print("All expected servers are healthy.")
            print(f"Running {args.queries} queries for {domain}...")

            rows, summary = run_experiment(
                args.queries,
                domain,
                args.scenario
            )

            save_results(rows, summary, args.servers)

            print("\n========== EXPERIMENT SUMMARY ==========")
            for key, value in summary.items():
                print(f"{key}: {value}")
            print("========================================")

    finally:
        stop_local_servers(processes)

        if receiver:
            receiver.stop()

        resolver.SERVER_IPS = old_ips
        resolver.SERVER_PORTS = old_ports
        resolver.HEARTBEAT_FILE = old_heartbeat_file


if __name__ == "__main__":
    main()
