# Experimental Performance Analysis

## 1. Objective

Evaluate the performance of the UDP DNS-like resolution system
under different server configurations.

## 2. Experimental Configurations

The normal workload used 100 queries with:
- 1 DNS server
- 3 DNS servers
- 5 DNS servers

All experiments were performed sequentially on localhost,
using unique UDP ports.

## 3. Results

| DNS Servers | Queries | Average Latency (ms) | Throughput (QPS) |
|---|---:|---:|---:|
| 1 | 100 | 0.1776 | 5631.90 |
| 3 | 100 | 0.2041 | 4899.59 |
| 5 | 100 | 0.2144 | 4664.90 |

## 4. Observations

1. The single-server configuration recorded the lowest
   average latency.
2. The single-server configuration recorded the highest
   throughput in these experiments.
3. Average latency increased slightly as the number of
   configured servers increased.
4. These are sequential local application-level benchmarks.
5. The results do not demonstrate real distributed network
   load balancing or OpenFlow performance.

## 5. Negative Lookup Testing

A separate missing-domain experiment sent 100 queries.

Results:
- NOT_FOUND: 100
- SERVFAIL: 0
- Successful positive resolutions: 0

The NOT_FOUND responses indicate that the resolver correctly
identified nonexistent domain names.

## 6. Limitations

- Experiments used localhost and unique UDP ports.
- The tests were sequential rather than concurrent.
- No real Mininet/Open vSwitch network measurements are
  represented here.
- Results should not be generalized to production networks.

## 7. Conclusion

The local experiments demonstrate successful UDP resolution
and provide baseline latency and throughput measurements.
Further testing in Mininet with Ryu is required to evaluate
distributed server selection, failure handling and SDN
controller behaviour.

## 8. Additional Benchmark Results — November 16, 2026

Environment:
- Operating System: macOS
- Python: 3.13.5
- Protocol: UDP
- Network: localhost (127.0.0.1)
- Workload: 100 sequential queries per configuration
- DNS server configurations: 1, 3 and 5

### Results

| DNS Servers | Queries | Successful | Failed | Average Latency (ms) | P95 Latency (ms) | Throughput (QPS) |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 100 | 100 | 0 | 1.4469 | 3.9101 | 691.11 |
| 3 | 100 | 100 | 0 | 0.9975 | 1.9170 | 1002.54 |
| 5 | 100 | 100 | 0 | 0.8882 | 1.3263 | 1125.85 |

### Observations

1. All three configurations completed 100 queries successfully.
2. No failed queries were recorded.
3. The five-server configuration recorded the lowest average latency in this run.
4. The five-server configuration also recorded the highest throughput.
5. The measurements are sequential localhost application-level results, not concurrent stress tests or Mininet network measurements.

### Conclusion

The benchmark runs demonstrate successful UDP DNS-like resolution
with 1, 3 and 5 server configurations. Further repeated and
concurrent experiments would be required to establish scalability
and performance trends.
