import { describe, expect, it } from "vitest";
import {
  RPC_MALFORMED_ENVELOPE,
  RPC_REMOTE_GENERIC,
  RPC_THREAD_POOL_EXHAUSTED,
  RemoteFatalRPCError,
  RemoteRecoverableRPCError,
  clampAsapRpcSlot,
  isAsapJsonRpcCode,
  remoteRpcErrorFromJson,
  remoteRpcErrorFromJsonRpcError,
} from "../src/errors.js";

describe("errors RPC taxonomy", () => {
  it("classifies ASAP JSON-RPC codes in the reserved band", () => {
    expect(isAsapJsonRpcCode(-32059)).toBe(true);
    expect(isAsapJsonRpcCode(-32000)).toBe(true);
    expect(isAsapJsonRpcCode(-31999)).toBe(false);
    expect(clampAsapRpcSlot(-32031)).toBe(RPC_THREAD_POOL_EXHAUSTED);
    expect(clampAsapRpcSlot(-32603)).toBe(RPC_REMOTE_GENERIC);
  });

  it("remoteRpcErrorFromJson uses recoverable flag for RemoteRecoverableRPCError", () => {
    const err = remoteRpcErrorFromJson(RPC_THREAD_POOL_EXHAUSTED, "busy", {
      recoverable: true,
      retry_after_ms: 100,
      asap_taxonomy_code: "asap:transport/thread_pool_exhausted",
    });
    expect(err).toBeInstanceOf(RemoteRecoverableRPCError);
    if (err instanceof RemoteRecoverableRPCError) {
      expect(err.jsonRpcCode).toBe(RPC_THREAD_POOL_EXHAUSTED);
      expect(err.retryAfterMs).toBe(100);
      expect(err.code).toBe("asap:transport/thread_pool_exhausted");
    }
  });

  it("remoteRpcErrorFromJson yields RemoteFatalRPCError when recoverable is not true", () => {
    const err = remoteRpcErrorFromJson(RPC_MALFORMED_ENVELOPE, "bad envelope", {
      recoverable: false,
    });
    expect(err).toBeInstanceOf(RemoteFatalRPCError);
    if (err instanceof RemoteFatalRPCError) {
      expect(err.jsonRpcCode).toBe(RPC_MALFORMED_ENVELOPE);
      expect(err.rpcCode).toBe(RPC_MALFORMED_ENVELOPE);
    }
  });

  it("remoteRpcErrorFromJsonRpcError parses wire error object", () => {
    const err = remoteRpcErrorFromJsonRpcError({
      code: RPC_MALFORMED_ENVELOPE,
      message: "nope",
      data: { recoverable: true, retry_after_ms: 0 },
    });
    expect(err).toBeInstanceOf(RemoteRecoverableRPCError);
  });

  it("pop remote meta filters alternative_agents and maps fallback_action", () => {
    const err = RemoteFatalRPCError.fromJsonRpc(RPC_REMOTE_GENERIC, "try others", {
      alternative_agents: ["urn:a:ok", 42, "urn:b:ok"],
      fallback_action: "retry_later",
    });
    expect(err.alternativeAgents).toEqual(["urn:a:ok", "urn:b:ok"]);
    expect(err.fallbackAction).toBe("retry_later");
  });

  it("pop remote meta applies asap taxonomy from data.code when present", () => {
    const err = RemoteFatalRPCError.fromJsonRpc(RPC_REMOTE_GENERIC, "typed", {
      code: "asap:capabilities/unsupported",
      detail: "x",
    });
    expect(err.taxonomyCode).toBe("asap:capabilities/unsupported");
    expect((err.details as { detail?: string }).detail).toBe("x");
  });

  it("omits alternativeAgents when every entry is non-string", () => {
    const err = RemoteFatalRPCError.fromJsonRpc(RPC_REMOTE_GENERIC, "none", {
      alternative_agents: [1, {}, null],
    });
    expect(err.alternativeAgents).toBeUndefined();
  });
});
