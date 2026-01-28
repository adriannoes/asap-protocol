# Error Handling

This document describes ASAP error taxonomy and handling patterns.

## Error Taxonomy

ASAP defines structured errors in `asap.errors` with a stable error code format:

```
asap:<domain>/<error>
```

Examples:

- `asap:protocol/invalid_state`
- `asap:protocol/malformed_envelope`
- `asap:task/not_found`

## Core Error Types

- `ASAPError`: base class for all protocol errors
- `InvalidTransitionError`: invalid task state transitions
- `MalformedEnvelopeError`: invalid envelope payloads
- `TaskNotFoundError`: task lookup failures
- `TaskAlreadyCompletedError`: attempted updates to terminal tasks

## Usage Example

```python
from asap.errors import InvalidTransitionError

try:
    raise InvalidTransitionError(from_state="submitted", to_state="completed")
except InvalidTransitionError as exc:
    error_payload = exc.to_dict()
    # error_payload contains code, message, and details
```

## JSON-RPC Mapping

Transport layer errors are surfaced as JSON-RPC error responses:

- `INVALID_REQUEST` for malformed JSON-RPC requests
- `INVALID_PARAMS` for invalid envelope payloads
- `METHOD_NOT_FOUND` for unknown payload types
- `INTERNAL_ERROR` for unexpected exceptions

Use structured logs with `trace_id` and `correlation_id` to debug failures across
agent boundaries.

---

## Connection Error Troubleshooting

Connection errors are common when communicating with remote ASAP agents. This section provides guidance on diagnosing and resolving connection issues.

### Common Connection Errors

#### ASAPConnectionError

Raised when the HTTP connection cannot be established or when the remote server returns an HTTP error status.

**Error Message Format**:
```
Connection failed to {url}. Verify the agent is running and accessible.
Troubleshooting: Check the URL format, network connectivity, and firewall settings.
```

**Common Causes**:

1. **Agent Not Running**: The target agent service is not started or has crashed
2. **Incorrect URL**: The base URL is malformed or points to the wrong endpoint
3. **Network Issues**: Firewall blocking, DNS resolution failures, or network unreachable
4. **Port Mismatch**: The agent is running on a different port than specified
5. **HTTPS/HTTP Mismatch**: Using HTTP when HTTPS is required (or vice versa)

**Diagnostic Steps**:

```python
from asap.transport.client import ASAPClient
from asap.errors import ASAPConnectionError

async def diagnose_connection(base_url: str):
    """Diagnose connection issues with an ASAP agent."""
    try:
        async with ASAPClient(base_url=base_url) as client:
            # Try to validate connection
            is_valid = await client._validate_connection()
            if is_valid:
                print(f"✓ Connection to {base_url} is valid")
            else:
                print(f"✗ Connection validation failed for {base_url}")
    except ASAPConnectionError as e:
        print(f"Connection Error: {e.message}")
        print(f"URL: {e.url}")
        print("\nTroubleshooting steps:")
        print("1. Verify the agent is running:")
        print(f"   curl {base_url}/.well-known/asap/manifest.json")
        print("2. Check URL format (should be http:// or https://)")
        print("3. Verify network connectivity:")
        print(f"   ping {base_url.split('://')[1].split('/')[0]}")
        print("4. Check firewall settings")
        print("5. Verify port is correct")
```

#### ASAPTimeoutError

Raised when the HTTP request exceeds the configured timeout duration.

**Error Message Format**:
```
Request to {url} timed out after {timeout} seconds
```

**Common Causes**:

1. **Slow Network**: High latency or slow network connection
2. **Server Overload**: Server is processing requests slowly
3. **Timeout Too Short**: Configured timeout is insufficient for the operation
4. **Large Payload**: Request/response payload is large and takes time to transfer

**Solutions**:

```python
# Increase timeout for slow connections
async with ASAPClient(
    base_url="https://api.example.com",
    timeout=120.0  # 2 minutes instead of default 60 seconds
) as client:
    response = await client.send(envelope)

# For large payloads, consider:
# - Splitting into smaller requests
# - Using streaming for large responses
# - Increasing both client and server timeouts
```

#### CircuitOpenError

Raised when the circuit breaker is open and requests are rejected immediately.

**Error Message Format**:
```
Circuit breaker is OPEN for {base_url}. Too many consecutive failures ({count}).
Service temporarily unavailable.
```

**Common Causes**:

1. **Service Down**: The remote service is completely unavailable
2. **High Failure Rate**: Multiple consecutive failures have occurred
3. **Network Partition**: Network connectivity issues causing repeated failures

**Solutions**:

```python
from asap.errors import CircuitOpenError

try:
    async with ASAPClient(
        base_url="https://api.example.com",
        circuit_breaker_enabled=True
    ) as client:
        response = await client.send(envelope)
except CircuitOpenError as e:
    print(f"Circuit is open: {e.message}")
    print(f"Consecutive failures: {e.consecutive_failures}")
    print("\nSolutions:")
    print("1. Wait for circuit breaker timeout (default: 60s)")
    print("2. Check if remote service is operational")
    print("3. Verify network connectivity")
    print("4. Consider disabling circuit breaker if failures are expected")
```

### Diagnostic Checklist

When experiencing connection errors, follow this checklist:

#### 1. Verify Agent is Running

```bash
# Check if agent is accessible
curl -I https://api.example.com/.well-known/asap/manifest.json

# Expected: HTTP/1.1 200 OK
# If 404: Agent may not be running or URL is incorrect
# If connection refused: Agent is not listening on that port
```

#### 2. Check URL Format

```python
# Valid URLs
"https://api.example.com"           # ✓ HTTPS production
"http://localhost:8000"             # ✓ HTTP localhost (development)
"https://localhost:8443"            # ✓ HTTPS localhost

# Invalid URLs
"api.example.com"                   # ✗ Missing scheme
"ftp://api.example.com"             # ✗ Unsupported scheme
"http://api.example.com"            # ✗ HTTP in production (if require_https=True)
```

#### 3. Test Network Connectivity

```bash
# Test DNS resolution
nslookup api.example.com

# Test TCP connection
telnet api.example.com 443

# Test HTTP connection
curl -v https://api.example.com/.well-known/asap/manifest.json
```

#### 4. Verify Firewall and Security Groups

- **Outbound Rules**: Ensure your client can make outbound HTTPS connections
- **Inbound Rules**: Ensure the agent server accepts inbound connections on the configured port
- **Security Groups**: Check cloud provider security group rules (AWS, GCP, Azure)

#### 5. Check SSL/TLS Configuration

```python
# For development with self-signed certificates
async with ASAPClient(
    base_url="https://localhost:8443",
    verify_ssl=False  # ⚠️ Development only, not for production
) as client:
    response = await client.send(envelope)
```

#### 6. Review Error Logs

The ASAP client provides structured logging with context:

```python
import logging
from asap.observability import get_logger

logger = get_logger(__name__)

# Logs include:
# - target_url: The URL being accessed
# - attempt: Retry attempt number
# - status_code: HTTP status code (if available)
# - error: Error message
# - delay_seconds: Backoff delay before retry
```

### Best Practices for Error Handling

#### 1. Implement Retry Logic

The client includes automatic retry with exponential backoff, but you can add custom retry logic:

```python
from asap.transport.client import ASAPClient
from asap.errors import ASAPConnectionError, ASAPTimeoutError
import asyncio

async def send_with_custom_retry(envelope, max_attempts=3):
    """Send envelope with custom retry logic."""
    for attempt in range(max_attempts):
        try:
            async with ASAPClient(base_url="https://api.example.com") as client:
                return await client.send(envelope)
        except (ASAPConnectionError, ASAPTimeoutError) as e:
            if attempt == max_attempts - 1:
                raise  # Last attempt failed
            wait_time = 2 ** attempt  # Exponential backoff
            print(f"Attempt {attempt + 1} failed, retrying in {wait_time}s...")
            await asyncio.sleep(wait_time)
```

#### 2. Handle Circuit Breaker Gracefully

```python
from asap.errors import CircuitOpenError

try:
    response = await client.send(envelope)
except CircuitOpenError:
    # Circuit is open, use fallback or queue for later
    print("Service unavailable, using fallback")
    return fallback_response()
```

#### 3. Validate Connection Before Sending

```python
async with ASAPClient(base_url="https://api.example.com") as client:
    # Optional: Validate connection before sending
    is_valid = await client._validate_connection()
    if not is_valid:
        print("Connection validation failed, but attempting anyway...")
    
    # Send envelope (will retry automatically on failure)
    response = await client.send(envelope)
```

#### 4. Monitor and Alert

Set up monitoring for connection errors:

```python
from asap.errors import ASAPConnectionError
import metrics

async def monitored_send(client, envelope):
    """Send envelope with error monitoring."""
    try:
        response = await client.send(envelope)
        metrics.increment("asap.requests.success")
        return response
    except ASAPConnectionError as e:
        metrics.increment("asap.requests.connection_error")
        metrics.increment(f"asap.errors.connection.{e.url}")
        # Send alert if error rate is high
        raise
```

### Example: Complete Error Handling

```python
from asap.transport.client import ASAPClient
from asap.errors import (
    ASAPConnectionError,
    ASAPTimeoutError,
    CircuitOpenError,
    ASAPRemoteError,
)
from asap.models.envelope import Envelope

async def robust_send(envelope: Envelope, base_url: str):
    """Send envelope with comprehensive error handling."""
    try:
        async with ASAPClient(
            base_url=base_url,
            timeout=30.0,
            max_retries=3,
            circuit_breaker_enabled=True,
        ) as client:
            response = await client.send(envelope)
            return response
            
    except CircuitOpenError as e:
        print(f"Circuit breaker is open: {e.message}")
        print("Service is temporarily unavailable. Please try again later.")
        raise
        
    except ASAPConnectionError as e:
        print(f"Connection failed: {e.message}")
        print(f"Troubleshooting:")
        print(f"1. Verify agent is running at {e.url}")
        print(f"2. Check network connectivity")
        print(f"3. Verify URL format and port")
        raise
        
    except ASAPTimeoutError as e:
        print(f"Request timed out after {e.timeout} seconds")
        print("Consider increasing timeout or checking network latency")
        raise
        
    except ASAPRemoteError as e:
        print(f"Remote error: {e.code} - {e.message}")
        print(f"Error details: {e.data}")
        raise
```

### Related Documentation

- [Transport Guide](transport.md) - HTTP/JSON-RPC binding details
- [Security Guide](security.md) - Authentication and TLS configuration
- [Observability](observability.md) - Logging and tracing for debugging
