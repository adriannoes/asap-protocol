# Code Review: PR #20 (S4 Retry & Auth)

## 1. Executive Summary
* **Impact Analysis:** **Medium-High Risk**. The core retry and circuit breaker logic is solid, but a critical gap in exception handling (Timeouts) compromises the improved resilience.
* **Architecture Check:** **Yes**. The implementation aligns well with the planned architecture, utilizing decorators, efficient constants, and proper layering.
* **Blockers:** **1** critical issue found (Unhandled Timeouts).

## 2. Critical Issues (Must Fix)
*Issues that cause bugs, security risks, or strictly violate architecture/linting rules.*

### Unhandled Request Timeouts - src/asap/transport/client.py
* **Location:** Lines 613-800 (`send` method retry loop)
* **Problem:** The current implementation catches `httpx.ConnectError` but fails to catch `httpx.TimeoutException`. If a request times out (network stall, firewall, slow server), the exception will bubble up immediately, bypassing the retry logic and, critically, **failing to record the failure in the Circuit Breaker**. This defeat the purpose of the circuit breaker for one of its most important use cases (unresponsive services).
* **Recommendation:** Catch `httpx.TimeoutException`, record the failure, and trigger the retry logic.

```diff
-            except httpx.ConnectError as e:
-                error_msg = (
-                    f"Connection error to {self.base_url}: {e}. "
-                    f"Verify the agent is running and accessible."
-                )
-                last_exception = ASAPConnectionError(error_msg, cause=e, url=self.base_url)
-                # Log retry attempt
-                if attempt < self.max_retries - 1:
-                    delay = self._calculate_backoff(attempt)
-                    logger.warning(
-                        "asap.client.retry",
-                        # ...
-                    )
-                    logger.info(...)
-                    await asyncio.sleep(delay)
-                    continue
+            except (httpx.ConnectError, httpx.TimeoutException) as e:
+                is_timeout = isinstance(e, httpx.TimeoutException)
+                error_type = "Timeout" if is_timeout else "Connection error"
+                error_msg = (
+                    f"{error_type} to {self.base_url}: {e}. "
+                    f"Verify the agent is running and accessible."
+                )
+                last_exception = ASAPConnectionError(error_msg, cause=e, url=self.base_url)
+                
+                # Log retry attempt
+                if attempt < self.max_retries - 1:
+                    delay = self._calculate_backoff(attempt)
+                    logger.warning(
+                        "asap.client.retry",
+                        # ... args ...
+                        message=f"{error_type}, retrying in {delay:.2f}s..."
+                    )
+                    await asyncio.sleep(delay)
+                    continue
+
+                # Retries exhausted: Record failure in Circuit Breaker
+                if self._circuit_breaker is not None:
+                    self._circuit_breaker.record_failure()
+                    # Log circuit state change if needed (copy logic from 5xx handler)
+
+                raise last_exception
```

## 3. Improvements & Refactoring (Strongly Recommended)

### Circuit Breaker Reset on Remote Error - src/asap/transport/client.py
- **Location:** Lines 741-748 (`ASAPRemoteError` handling)
- **Context:** If the server responds with a valid JSON-RPC error (e.g., `-32603` or "Method not found"), it means the *connection* and *transport* are healthy. Currently, this path does not call `record_success()`, so the circuit breaker acts as if the request never succeeded (failure count isn't reset). This could lead to a "stale" failure count effectively reducing the threshold for subsequent real failures.
- **Suggestion:** Consider a valid JSON-RPC error as a "Success" from the Circuit Breaker's perspective (service is reachable).

```diff
                 # Check for JSON-RPC error
                 if "error" in json_response:
+                    # Record success pattern (service is reachable)
+                    if self._circuit_breaker is not None:
+                        self._circuit_breaker.record_success()
+                        
                     error = json_response["error"]
                     raise ASAPRemoteError(...)
```

### Robust Retry-After Parsing - src/asap/transport/client.py
- **Location:** Line 676
- **Context:** The HTTP `Retry-After` header can be an HTTP Date string. The current implementation only supports seconds (`float`).
- **Suggestion:** Add support for Date parsing using `email.utils.parsedate_to_datetime`.

```diff
-                                delay = float(retry_after)
+                                # Simple check for digit, else try date parsing
+                                if retry_after.replace('.', '', 1).isdigit():
+                                    delay = float(retry_after)
+                                else:
+                                    # Add date parsing logic here (or TODO)
+                                    # from email.utils import parsedate_to_datetime
+                                    # ... calculate delta ...
```

## 4. Nitpicks & Questions

*   **[src/asap/transport/client.py] (Line 368)**: `self._request_counter` is updated with `+= 1` which is not atomic across threads. Since `CircuitBreaker` uses `RLock`, there is an implication of thread-safety. If `ASAPClient` is shared across threads, this could cause ID collisions. Consider using `itertools.count` and `next()` or a lock if thread safety is a requirement.

*   **[src/asap/transport/client.py] (Line 284)**: The `__init__` method argument list is getting very long (11 args). Consider grouping the retry/circuit-breaker configs into a `RetryConfig` dataclass/pydantic model to avoid `False, 5, 60.0` boolean trap issues and clean up the signature.
