/**
 * Transport helpers: retry on recoverable errors (TS-011).
 *
 * Aligns with Python `ASAPClient.send` retry when `retry_after_ms` is present on
 * {@link RecoverableError} or {@link RemoteRecoverableRPCError}.
 */

import { RecoverableError, RemoteRecoverableRPCError } from "./errors.js";

export interface RecoverableRetryOptions {
  /** Maximum number of attempts including the first (default 8). */
  readonly maxRetries?: number;
  /** Injected sleep for tests (default `setTimeout` promise). */
  readonly sleep?: (ms: number) => Promise<void>;
}

function defaultSleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

function recoverableRetryDelayMs(error: unknown): number | undefined {
  if (error instanceof RemoteRecoverableRPCError) {
    if (error.retryAfterMs === undefined) {
      return undefined;
    }
    return Math.max(0, error.retryAfterMs);
  }
  if (error instanceof RecoverableError) {
    if (error.retryAfterMs === undefined) {
      return undefined;
    }
    return Math.max(0, error.retryAfterMs);
  }
  return undefined;
}

/**
 * Runs `op`, retrying when it throws {@link RecoverableError} or
 * {@link RemoteRecoverableRPCError} with a defined `retryAfterMs` (mirrors Python
 * client behaviour for JSON-RPC recoverable errors).
 */
export async function callWithRecoverableRetry<T>(
  op: () => Promise<T>,
  options?: RecoverableRetryOptions,
): Promise<T> {
  const maxRetries = options?.maxRetries ?? 8;
  const sleep = options?.sleep ?? defaultSleep;
  let attempt = 0;
  for (;;) {
    try {
      return await op();
    } catch (e) {
      const delayMs = recoverableRetryDelayMs(e);
      if (delayMs === undefined || attempt >= maxRetries - 1) {
        throw e;
      }
      await sleep(delayMs);
      attempt += 1;
    }
  }
}
