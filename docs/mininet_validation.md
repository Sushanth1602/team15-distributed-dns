# Mininet SDN Integration Validation

## Environment
- Host: MacBook Apple Silicon M4
- VM: VMware Fusion
- Guest OS: Ubuntu 24.04 ARM64
- Network emulator: Mininet and Open vSwitch
- Controller: OS-Ken, OpenFlow 1.3
- DNS servers: Five
- DNS transport: UDP port 5353
- Heartbeat receiver: UDP port 9999

## Functional test results

| Test | Observation | Result |
|---|---|---|
| Topology connectivity | Earlier pingall: 56/56 received, 0% loss | PASS |
| Known domain | video.lab resolved successfully | PASS |
| Unknown domain | unknown.lab returned NOT_FOUND | PASS |
| Round robin | Server-specific responses from DNS1 through DNS5 observed | PASS |
| Client cache | Repeated lookup was served from cache | PASS |
| DNS3 failure detection | Heartbeat became stale; controller logged 10.0.0.13 FAILED | PASS |
| Failover | Five fresh queries succeeded while DNS3 was stopped | PASS |
| DNS3 recovery | Fresh heartbeat observed and a subsequent query was served by DNS3 | PASS |

## Failover evidence

With DNS3 stopped, five fresh video.lab requests returned:
- DNS4: 10.0.4.11
- DNS5: 10.0.5.11
- DNS1: 10.0.1.11
- DNS2: 10.0.2.11
- DNS4: 10.0.4.11

Client statistics: 5 network lookups, 5 successes, 0 failures, 0 retries.

After DNS3 was restarted, its heartbeat age was measured at 0.98 seconds. A subsequent batch of five successful requests included a response from DNS3: 10.0.3.11.

The controller log captured the FAILED event. Recovery is supported by the fresh heartbeat and successful DNS3 response; a RECOVERED log line was not observed in the captured log.

## Network-only performance sample

The client cache was cleared before each of 30 lookups.

| Metric | Result |
|---|---:|
| Total queries | 30 |
| Successful | 30 |
| Failed | 0 |
| Cache hits | 0 |
| Success rate | 100% |
| Average reported latency | 0.800 ms |
| Minimum reported latency | 0.417 ms |
| Maximum reported latency | 3.480 ms |

## Cache-enabled sample

A separate 30-query run recorded:
- 30 successful responses
- 1 network lookup (first lookup: 1.580 ms)
- 29 cache hits (reported latency between 0 and 0.002 ms)

## Interpretation and limitations

These are sequential client-reported measurements in the VMware/Mininet environment. They are not concurrent stress-test results or production-network benchmarks.

The Mininet SDN path was validated through the controller's server selection and traffic steering. These observations should be distinguished from the separate application-level resolver unit and integration tests.

## Recovery logging clarification

The Member 3 controller log excerpt captured the DNS3 FAILED event.
A teammate independently confirmed that another controller run logged
both FAILED and RECOVERED transitions, followed by a DNS redirect to DNS3.
The fresh heartbeat and successful DNS3 response were also observed in
the Member 3 run.
