import json
import os
import socket
import time

HOST = "10.0.0.100"
PORT = 9999
HEARTBEAT_FILE = "/tmp/team15_heartbeats.json"

heartbeats = {}

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((HOST, PORT))

print(f"Heartbeat receiver listening on {HOST}:{PORT}", flush=True)

while True:
    try:
        data, address = sock.recvfrom(4096)
        message = json.loads(data.decode())

        server_id = message.get("server_id")

        if server_id:
            heartbeats[server_id] = time.time()

            temp_file = HEARTBEAT_FILE + ".tmp"

            with open(temp_file, "w") as file:
                json.dump(heartbeats, file)

            os.replace(temp_file, HEARTBEAT_FILE)

            print(f"Heartbeat received from {server_id}", flush=True)

    except (json.JSONDecodeError, UnicodeDecodeError):
        print("Ignored invalid heartbeat", flush=True)

    except Exception as error:
        print(f"Heartbeat receiver error: {error}", flush=True)
