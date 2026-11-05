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

These tests do not independently prove real network-level
OpenFlow traffic redirection or Mininet failure recovery.

Actual SDN validation with Mininet, Open vSwitch and Ryu
remains pending.

## 7. Conclusion

The resolver's tested failure-handling mechanisms behaved
as expected in the local test environment.
Further network emulation is required to validate the
complete distributed SDN architecture.
