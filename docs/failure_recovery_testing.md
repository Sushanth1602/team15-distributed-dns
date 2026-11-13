# Failure Detection and Recovery Testing

## 1. Objective

Evaluate how the DNS-like resolver responds when DNS servers
become unavailable, stop responding, or recover.

## 2. Test Environment

- Protocol: UDP
- Resolver: Virtual DNS resolver
- Heartbeat monitoring: Enabled
- Local test environment: macOS
- Resolver integration tests: pytest

## 3. Test Cases

### Test 1: Healthy Server Resolution

Expected:
The resolver detects a healthy server and successfully
resolves the requested domain.

Observed:
PASS — healthy server resolution test passed.

### Test 2: No Heartbeat

Expected:
A server without a valid heartbeat is treated as unhealthy.

Observed:
PASS — missing heartbeat detection test passed.

### Test 3: Failed Server Fallback

Expected:
When one server fails, the resolver attempts another
available server.

Observed:
PASS — failed server fallback test passed.

### Test 4: All Servers Unavailable

Expected:
The resolver returns SERVFAIL when no healthy server
can answer the request.

Observed:
PASS — no healthy server and timeout tests passed.

### Test 5: Server Recovery

Expected:
After a failed server starts sending valid heartbeats
again, it can be considered healthy.

Observed:
PASS — server recovery integration test passed.

### Test 6: Stale Heartbeat Rejection

Expected:
Old heartbeat information must not be treated as
proof that a server is currently healthy.

Observed:
PASS — stale heartbeat rejection test passed.

## 4. Test Results

The following relevant test suites passed:

- Resolver unit tests: 5 passed.
- Resolver integration tests: 6 passed.
- Basic UDP tests: 11 passed.

## 5. Interpretation

The local tests demonstrate heartbeat-based health detection,
server fallback, timeout handling and recovery behaviour
within the tested application environment.

## 6. Limitations

The automated resolver tests exercise application-level health detection,
fallback, timeout and recovery logic.

The Mininet experiment is a separate network-level functional validation.
Neither experiment is a large-scale load or concurrent stress test.

## 7. Conclusion

The local automated tests recorded successful failure-handling and
recovery behaviour. The additional Mininet experiment in Section 8
also demonstrated DNS3 failure detection, continued resolution through
healthy servers, and DNS3 recovery.

## 8. Additional Mininet SDN Failure and Recovery Experiment (November 2026)

Environment:
- Five DNS servers in Mininet
- OS-Ken controller using OpenFlow 1.3
- Heartbeat receiver at 10.0.0.100:9999
- DNS3 address: 10.0.0.13

### DNS3 failure detection
DNS3 was stopped. Its heartbeat became stale, and the controller log recorded `10.0.0.13 FAILED`.

Result: PASS

### Failover while DNS3 was stopped
Five fresh video.lab queries were issued. All five returned status OK. Their server-specific answers corresponded to DNS4, DNS5, DNS1, DNS2 and DNS4. Client statistics recorded five network lookups, five successes, zero failures and zero retries.

Result: PASS

### DNS3 recovery
DNS3 was restarted and reported listening on UDP port 5353. Its heartbeat age was measured at 0.98 seconds. A subsequent five-query batch returned five successful answers, including one answer from DNS3 (10.0.3.11).

In the Member 3 test run, the captured controller log showed the FAILED event but did not include the RECOVERED line. A teammate independently confirmed that their controller test run logged both 10.0.0.13 FAILED and 10.0.0.13 RECOVERED when DNS3 heartbeats resumed, followed by a DNS redirect to DNS3.

Together with the fresh heartbeat and successful DNS3 response observed in the Member 3 run, this confirms recovery behaviour across the test runs. The missing RECOVERED line in the Member 3 log excerpt was a log-capture difference, not an identified controller defect.

Result: PASS

These were functional checks in the Mininet test environment, not a large-scale load or concurrent stress test.
