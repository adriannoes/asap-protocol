import { describe, expect, it, vi } from "vitest";
import {
  RecoverableError,
  RemoteFatalRPCError,
  RemoteRecoverableRPCError,
  RPC_MALFORMED_ENVELOPE,
  RPC_THREAD_POOL_EXHAUSTED,
} from "../src/errors.js";
import { callWithRecoverableRetry } from "../src/transport.js";

describe("transport retry", () => {
  it("retries after local RecoverableError when retryAfterMs is defined", async () => {
    let calls = 0;
    const op = vi.fn().mockImplementation(async () => {
      calls += 1;
      if (calls === 1) {
        throw new RecoverableError({ code: "RATE_LIMIT", retryAfterMs: 0 });
      }
      return { ok: true as const };
    });

    const sleep = vi.fn(async () => {
      /* immediate for test speed */
    });
    const result = await callWithRecoverableRetry(op, { sleep });
    expect(result).toEqual({ ok: true });
    expect(op).toHaveBeenCalledTimes(2);
    expect(sleep).toHaveBeenCalledWith(0);
  });

  it("retries after RemoteRecoverableRPCError with retryAfterMs", async () => {
    let calls = 0;
    const op = vi.fn().mockImplementation(async () => {
      calls += 1;
      if (calls === 1) {
        throw new RemoteRecoverableRPCError({
          wireJsonRpcCode: RPC_THREAD_POOL_EXHAUSTED,
          message: "pool full",
          retryAfterMs: 0,
        });
      }
      return { ok: 2 as const };
    });

    const result = await callWithRecoverableRetry(op, {
      sleep: vi.fn(async () => {
        /* noop */
      }),
    });
    expect(result).toEqual({ ok: 2 });
    expect(op).toHaveBeenCalledTimes(2);
  });

  it("does not retry RemoteFatalRPCError", async () => {
    const fatal = RemoteFatalRPCError.fromJsonRpc(RPC_MALFORMED_ENVELOPE, "bad", {});
    const op = vi.fn().mockRejectedValue(fatal);
    await expect(callWithRecoverableRetry(op, { maxRetries: 5 })).rejects.toBe(fatal);
    expect(op).toHaveBeenCalledTimes(1);
  });

  it("stops after maxRetries when the operation keeps throwing recoverable errors", async () => {
    const op = vi.fn().mockImplementation(async () => {
      throw new RecoverableError({ code: "TRANSIENT", retryAfterMs: 0 });
    });
    await expect(
      callWithRecoverableRetry(op, {
        maxRetries: 3,
        sleep: vi.fn(async () => {
          /* noop */
        }),
      }),
    ).rejects.toMatchObject({ code: "TRANSIENT" });
    expect(op).toHaveBeenCalledTimes(3);
  });

  it("does not retry RecoverableError without retryAfterMs", async () => {
    const op = vi.fn().mockRejectedValue(new RecoverableError({ code: "NO_RETRY" }));
    await expect(
      callWithRecoverableRetry(op, {
        sleep: vi.fn(async () => {
          /* noop */
        }),
      }),
    ).rejects.toMatchObject({ code: "NO_RETRY" });
    expect(op).toHaveBeenCalledTimes(1);
  });

  it("does not retry RemoteRecoverableRPCError without retryAfterMs when no fallback backoff", async () => {
    const err = new RemoteRecoverableRPCError({
      wireJsonRpcCode: RPC_THREAD_POOL_EXHAUSTED,
      message: "no hint",
    });
    const op = vi.fn().mockRejectedValue(err);
    await expect(
      callWithRecoverableRetry(op, {
        sleep: vi.fn(async () => {
          /* noop */
        }),
      }),
    ).rejects.toBe(err);
    expect(op).toHaveBeenCalledTimes(1);
  });

  it("retries RecoverableError without retryAfterMs when fallbackBackoffMs is set", async () => {
    let calls = 0;
    const op = vi.fn().mockImplementation(async () => {
      calls += 1;
      if (calls === 1) {
        throw new RecoverableError({ code: "TRANSIENT_NO_HINT" });
      }
      return { ok: true as const };
    });
    const sleep = vi.fn(async () => {
      /* noop */
    });
    const result = await callWithRecoverableRetry(op, { fallbackBackoffMs: 100, sleep });
    expect(result).toEqual({ ok: true });
    expect(op).toHaveBeenCalledTimes(2);
    expect(sleep).toHaveBeenCalledWith(100);
  });

  it("caps fallback exponential backoff at 60 seconds", async () => {
    let calls = 0;
    const op = vi.fn().mockImplementation(async () => {
      calls += 1;
      if (calls <= 10) {
        throw new RecoverableError({ code: "TRANSIENT_NO_HINT" });
      }
      return calls;
    });
    const sleep = vi.fn(async () => {
      /* noop */
    });
    await callWithRecoverableRetry(op, {
      fallbackBackoffMs: 50_000,
      maxRetries: 12,
      sleep,
    });
    expect(sleep).toHaveBeenLastCalledWith(60_000);
  });

  it("retries RemoteRecoverableRPCError without retryAfterMs when fallbackBackoffMs is set", async () => {
    let calls = 0;
    const op = vi.fn().mockImplementation(async () => {
      calls += 1;
      if (calls === 1) {
        throw new RemoteRecoverableRPCError({
          wireJsonRpcCode: RPC_THREAD_POOL_EXHAUSTED,
          message: "no hint",
        });
      }
      return { ok: true as const };
    });
    const sleep = vi.fn(async () => {
      /* noop */
    });
    const result = await callWithRecoverableRetry(op, { fallbackBackoffMs: 200, sleep });
    expect(result).toEqual({ ok: true });
    expect(op).toHaveBeenCalledTimes(2);
    expect(sleep).toHaveBeenCalledWith(200);
  });

  it("uses default sleep when sleep is not injected", async () => {
    vi.useFakeTimers();
    let calls = 0;
    const op = vi.fn().mockImplementation(async () => {
      calls += 1;
      if (calls === 1) {
        throw new RecoverableError({ code: "HINTED", retryAfterMs: 0 });
      }
      return { ok: true as const };
    });
    const p = callWithRecoverableRetry(op, { maxRetries: 5 });
    await vi.runAllTimersAsync();
    await expect(p).resolves.toEqual({ ok: true });
    expect(op).toHaveBeenCalledTimes(2);
    vi.useRealTimers();
  });
});
