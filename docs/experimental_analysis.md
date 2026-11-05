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
