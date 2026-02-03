# Code Review: PR #32 (Observability & MCP)

## 1. Executive Summary

| Metric | Status | Details |
| :--- | :--- | :--- |
| **Impact Risk** | 🔴 **High** | Critical availability vulnerability in MCP server. |
| **Architecture** | 🟡 **Partial** | Strong structure but fails "Robustness" & "Security" pillars. |
| **Test Coverage** | 🟡 **Moderate** | Happy paths covered; critical error/transport paths missing. |
| **Blockers** | **3** | 1 Critical Security, 2 Medium Security. |

**Overview:**
The PR introduces the MCP protocol implementation and Grafana dashboards. While the code structure (Pydantic models, module separation) is excellent, the **transport layer (stdio)** is fragile. A single malformed request can crash the server (DoS), and there are significant gaps in input validation and error handling that must be addressed before production merge.

---

## 2. Security Critical Findings (Must Fix)

### [Critical] Denial of Service (DoS) via Malformed JSON
* **Vulnerability Description:** The server's main loop (`read_stdin`) terminates immediately upon receiving a line that cannot be parsed as JSON (`json.JSONDecodeError`). This violates the JSON-RPC specification (which requires sending a Parse Error `-32700`) and creates a trivial Denial of Service vector. Any connecting client (or line noise) sending non-JSON data will kill the service.
* **CWE:** CWE-755 (Improper Handling of Exceptional Conditions), CWE-400 (Resource Exhaustion).
* **Location:** `src/asap/mcp/server.py:228-229`
* **Test Case:** Run server and pipe `obvious_junk_data\n` to stdin. Server must stay alive and print a JSON error.
* **Remediation:**
```diff
# src/asap/mcp/server.py

        def read_stdin() -> dict[str, Any] | None:
            # ... checks ...
            try:
                data = json.loads(line)
                if not isinstance(data, dict):
-                   return None
+                   raise ValueError("Not a dictionary")
                return cast("dict[str, Any]", data)
            except json.JSONDecodeError:
-               return None
+               # Do not return None (which signals EOF). 
+               # Instead, return a specialized error dict or safely skip.
+               return {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
```

### [Medium] Information Disclosure via Exception Propagation
* **Vulnerability Description:** The `_handle_tools_call` method catches generic `Exception` and returns the raw `str(e)` to the client. If a tool fails with an exception containing sensitive data (e.g., database connection strings, paths, or keys), this information is leaked to the caller.
* **CWE:** CWE-209 (Generation of Error Message Containing Sensitive Information).
* **Location:** `src/asap/mcp/server.py:214`
* **Remediation:**
  Log the full exception internally. Return a sanitized "Internal Tool Error" message to the client unless the server is explicitly in `DEBUG` mode.

### [Medium] Missing Input Validation
* **Vulnerability Description:** The server allows tools to register an `inputSchema`, but it **does not validate** incoming tool arguments against this schema. Arguments are passed directly to the tool function. If the function expects an `int` and receives a `str`, it may crash or behave unpredictably (CWE-20).
* **Location:** `src/asap/mcp/server.py:207`
* **Remediation:**
  Implement explicit validation using the schema before invoking the tool.
  ```python
  # Pseudo-code
  validate(parsed.arguments, self._tools[parsed.name][1]) # schema
  ```

---

## 3. Test Coverage & Quality Verification

### Coverage Analysis
*   **Happy Paths (Pass):** ✅
    *   Integration tests (`test_mcp_test_server_client.py`) cover the full "list tools" -> "call tool" flow successfully.
    *   `test_asap_integration.py` correctly verifies the bridge between MCP and ASAP primitives.
*   **Error Paths (Incomplete):** ⚠️
    *   `test_mcp_tool_handles_asap_errors` checks ASAP client errors.
    *   **GAP:** No tests for **transport-level errors** (e.g., invalid JSON, blank lines, oversized inputs). This gap directly allowed the Critical DoS bug to slip through.
*   **Edge Cases (Missing):** ❌
    *   **Concurrency:** `test_concurrent_asap_tool_calls` uses a trivial delay. It does not verify that the server stays responsive to `ping/cancel` while a long tool runs (see Architecture section).

### Required New Tests
1.  **Transport Resilience Test:**
    *   **Scenario:** Write `{"jsonrpc": "2.0", ...` (partial line) or `Not JSON` to stdin.
    *   **Expectation:** Server writes valid JSON-RPC error response and **does not exit**.
2.  **Schema Enforcement Test:**
    *   **Scenario:** Call a tool that expects `{"age": int}` with `{"age": "failed"}`.
    *   **Expectation:** Server returns JSON-RPC `-32602` (Invalid Params) *without* invoking the Python function.

---

## 4. Architecture & Logic Review

### [Logic/Concurrency] Serial Request Processing
*   **Status:** **Fragile / Warning**
*   **Context:** `src/asap/mcp/server.py` awaits `_dispatch_request` inline within the consumer loop.
*   **Problem:** If a tool execution takes 10 seconds, the server cannot process *any* other messages (including `notifications/cancelled` or `ping`) during that time. The MCP spec encourages being able to cancel long-running requests.
*   **Recommendation:**
    *   **Short Term:** Document this limitation clearly.
    *   **Long Term (v1.1):** Use `asyncio.create_task` to background the tool execution, while maintaining a synchronized writer queue for responses.

### [Observability] Silent Failure on Transport
*   **Status:** **Needs Improvement**
*   **Context:** `read_stdin` returns `None` on `EOFError` or `OSError` without logging.
*   **Problem:** If the pipe breaks or is closed unexpectedly, the server dies silently, making debugging production issues significantly harder.
*   **Recommendation:** Add structured logging: `logger.debug("mcp.transport.closed", reason=str(e))` before returning `None`.

---

## 5. Nitpicks & Cleanup
*   **Protocol:** `src/asap/mcp/protocol.py` correctly uses `extra="ignore"` for forward compatibility. Keep this.
*   **Client:** `src/asap/mcp/client.py` defaults `request_id_type` to `"int"`. Consider switching to `"str"` by default for broader ecosystem compatibility (many LSP/MCP tools use UUIDs).
*   **Naming:** The internal method `_handle_tools_call` is well-named, but `run_stdio` could be renamed to `serve_stdio` to match the class intent better.

---

## 6. Security Scorecard

| Category | Status | Notes |
| :--- | :--- | :--- |
| **Injection Prevention** | 🟢 **Safe** | Uses `subprocess` with list args (no shell). |
| **Input Validation** | 🔴 **Fail** | Missing Schema validation, vulnerable to JSON DoS. |
| **Error Handling** | 🟠 **Risk** | Leaky exceptions; silent transport failures. |
| **Availability** | 🔴 **Fail** | Critical fragility in main loop. |
| **Auth/Access** | ⚪ **N/A** | MCP assumes trusted transport (stdio). |

---

## 7. Action Plan
1.  **Blocker Fix:** Patch `read_stdin` to handle `JSONDecodeError` (Security Critical).
2.  **Blocker Fix:** Add Schema validation logic to `_handle_tools_call`.
3.  **Test:** Add `test_transport_resilience.py` to cover "bad packets".
4.  **Refactor:** Add "Sanitized Error" wrapper for tool exceptions.
