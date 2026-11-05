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

- Local tests used loopback networking.
- Server configurations used unique UDP ports.
- Benchmarks were sequential, not concurrent.
- Actual Mininet and OpenFlow validation remains pending.
- Real distributed network performance has not yet been measured.

## 8. Pending Validation

- Mininet topology testing
- Ryu controller integration
- OpenFlow-based traffic steering
- Actual distributed server failure and recovery
- Network-level latency and throughput measurements

## 9. Conclusion

The local testing phase recorded 27 passing tests covering
basic UDP resolution, caching, TTL, resolver integration,
server failure handling and recovery.

Performance benchmarks and graphs were generated.

Actual SDN validation is still required before claiming
that the complete distributed DNS system has been validated.
