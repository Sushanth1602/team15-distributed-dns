# Distributed DNS-Like Name Resolution System
# Member 3 - Testing and Validation Report

## 1. Objective

Validate the UDP DNS-like resolution system through functional,
integration, cache, failure-handling and performance tests.

## 2. Testing Environment

- Operating System: macOS
- Language: Python
- Protocol: UDP
- Test framework: pytest
- Benchmark environment: localhost
- DNS server ports: 5301-5305

## 3. Functional Test Results

### Basic UDP Tests

Command:
python3 tests/test_basic.py

Result: 11/11 PASSED

Test coverage:
- Known domain resolution
- Unknown domain NOT_FOUND
- Cache hit
- TTL expiration
- Malformed packet handling
- Heartbeat reception
- Server-down retry handling
- Stale cache fallback
- Wrong-ID and duplicate reply handling
- Malformed reply handling
- Failure when only invalid replies are received

### Cache Tests

Command:
python3 -m pytest tests/test_cache.py -v -s

Result: 5/5 PASSED

Test coverage:
- Cache miss
- Cache hit
- TTL expiration
- Stale answer fallback
- NOT_FOUND not cached

### Resolver Integration Tests

Command:
python3 -m pytest tests/test_resolver_integration.py -v

Result: 6/6 PASSED

Test coverage:
- Healthy server resolution
- Genuine NOT_FOUND response
- No healthy servers
- Failed server fallback
- All servers timing out
- Server recovery

### Resolver Unit Tests

Command:
python3 -m pytest tests/test_resolver_unit.py -v

Result: 5/5 PASSED

Test coverage:
- Healthy server detection
- Missing heartbeat detection
- Valid server response
- Query server timeout
- Rejection of stale heartbeat

## 4. Overall Test Summary

| Test Suite | Passed |
|---|---:|
| Basic UDP | 11 |
| Cache | 5 |
| Resolver Integration | 6 |
| Resolver Unit | 5 |
| Total | 27 |

All 27 recorded tests passed.

## 5. Performance Testing

Three normal workload configurations were compared using
100 queries each.

| Servers | Queries | Average Latency (ms) | Throughput (QPS) |
|---|---:|---:|---:|
| 1 | 100 | 0.1776 | 5631.90 |
| 3 | 100 | 0.2041 | 4899.59 |
| 5 | 100 | 0.2144 | 4664.90 |

These are sequential localhost application-level measurements.
They do not establish real distributed load-balancing performance.

## 6. Negative Lookup Test

- Queries: 100
- NOT_FOUND: 100
- SERVFAIL: 0
- Positive resolutions: 0

The resolver correctly distinguished nonexistent names
from server failures in this experiment.

## 7. Limitations

- Earlier localhost tests used loopback networking and sequential queries.
- The Mininet performance sample contains 30 sequential queries, not a concurrent stress test.
- Results depend on the VM, host and measurement implementation.
- No production-scale capacity or Internet DNS performance claim is made.

## 8. Validation Scope and Remaining Work

- Functional Mininet and OpenFlow integration checks are documented in Section 10.
- Larger concurrent-load and scalability experiments remain future work.
- Production deployment and real-world network performance have not been established.

## 9. Conclusion

The local test phase recorded 27 passing tests.
The Mininet SDN topology was subsequently exercised for name resolution,
NOT_FOUND handling, round-robin selection, caching, server failure,
failover and recovery.

The experiments validate the tested paths in their stated environments,
but do not establish production-scale performance.

## 10. Additional Mininet/SDN Validation (November 2026)

The project was subsequently tested in a Mininet topology running under Ubuntu 24.04 ARM64 in VMware Fusion on an Apple Silicon Mac.

Observed functional results:
- Topology connectivity: earlier pingall reported 56/56 received and 0% loss.
- Known domain video.lab resolved successfully.
- Unknown domain unknown.lab returned NOT_FOUND.
- Server-specific answers from all five DNS servers were observed during round-robin testing.
- A repeated lookup was served from the client cache.
- Stopping DNS3 caused its heartbeat to become stale; the controller logged 10.0.0.13 FAILED.
- Five fresh lookups while DNS3 was stopped all succeeded, with 0 failures and 0 retries.
- After DNS3 restart, its heartbeat age was measured at 0.98 seconds and a subsequent query batch included a successful response from DNS3.

### Mininet network-only performance sample

The cache was cleared before each of 30 sequential lookups:
- Successful: 30/30
- Failed: 0
- Cache hits: 0
- Average reported latency: 0.800 ms
- Minimum reported latency: 0.417 ms
- Maximum reported latency: 3.480 ms

A separate cache-enabled 30-query run recorded 30 successes: one network lookup at 1.580 ms and 29 cache hits with reported latency between 0 and 0.002 ms.

The raw client result files are stored in `results/raw/`. These Mininet measurements are separate from the earlier localhost benchmarks and are not concurrent stress-test or production-network measurements.
