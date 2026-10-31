# Message Spec (Team 15, UDP DNS-like system)

All messages are JSON text sent in one UDP packet.

## Query (client -> resolver)
```json
{"id": 1234, "name": "video.lab", "type": "A"}
```
| field | meaning |
|-------|---------|
| id    | integer, new for every attempt (including retries), used to match the reply |
| name  | string, the name to look up |
| type  | string, only `"A"` is supported |

## Response (server -> client)
```json
{"id": 1234, "name": "video.lab", "ip": "10.0.1.11", "ttl": 30, "status": "OK"}
{"id": 1234, "name": "nope.lab", "ip": null, "ttl": 0, "status": "NOT_FOUND"}
```
| status    | meaning |
|-----------|---------|
| OK        | name found, `ip` and `ttl` are set |
| NOT_FOUND | name not in the server's records, `ip` is null |

## Heartbeat (server -> controller)
```json
{"server_id": "s1", "ts": 1730000000.0, "queries_served": 42}
```
Sent every 1 second over UDP to `10.0.0.100:9999` (set in `config/config.json`).
The switch forwards it to the controller as a packet-in. **Member 2 must confirm this path.**

## Query ID
The client gives every query a unique id. The server copies it into the reply.
The client only accepts a reply whose id matches the query it is waiting for.
Replies with an old, unknown or duplicate id are ignored. The reply's source IP is
NOT checked, because the controller rewrites addresses.

## Reply validation (client)
The client checks every reply before it accepts or caches it. A reply is accepted only if ALL of these hold:
1. It is a JSON object and its `id` equals the id of the query being waited for.
2. Its `name` is exactly the name that was asked for.
3. `status` is `OK` or `NOT_FOUND` (nothing else, case sensitive).
4. `ttl` is a whole number from 0 to 86400 (text, decimals, negatives and true/false are rejected).
5. If `status` is `OK`, `ip` is a proper dotted IPv4 address (like `10.0.1.11`).
   If `status` is `NOT_FOUND`, `ip` must be `null`.

Any other packet (not JSON, not an object, wrong name, bad status, bad ip, bad ttl) is ignored:
it is not cached, it does not end the attempt, and the client keeps waiting until the timeout.
Each ignored packet adds 1 to the `ignored_replies` counter in `get_stats()`.
If only bad replies arrive, the attempt times out like a lost reply and the normal retry rules apply.

## TTL
`ttl` is the number of seconds the client may keep the answer in its cache.
While the entry is fresh, the client answers from cache and sends no packet.
After the TTL ends the entry is deleted and a new query is sent.
Only `OK` answers are cached, never `NOT_FOUND`.

## Retry and fallback rules (client)
1. Check cache. Fresh hit -> return it, no packet sent.
2. Otherwise send the query to the virtual resolver and wait `timeout` (1 s).
3. No matching reply -> retry, up to `max_retries` (3) attempts in total.
4. All attempts failed -> if a stale (expired) cache entry exists, return it with `status: "STALE"`; otherwise return a clean failure (`status: "FAILED"`, `ip: null`).
5. The client never contacts real server IPs. Exception: baseline mode (`baseline_mode: true`) sends everything to the single `baseline_server` with no redirect.

## Malformed packets (server)
Bad JSON, non-dict, missing fields, wrong types, or type other than "A" are ignored: no reply, a log line only.

## Failed server (definition)
A server is failed if the controller gets no heartbeat from it for `max_missed` (3) intervals (3 s),
or if queries go to it but no replies come back.

## Record file format
`app/records/serverN.json` maps each name to its IP and TTL:
```json
{
  "video.lab": {"ip": "10.0.1.11", "ttl": 30},
  "web.lab":   {"ip": "10.0.1.12", "ttl": 3}
}
```
