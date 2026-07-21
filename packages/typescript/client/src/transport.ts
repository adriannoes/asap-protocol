/**
 * Recoverable JSON-RPC retries. Matches Python `ASAPClient.send` when `retry_after_ms`
 * is set; optional `fallbackBackoffMs` retries recoverable errors without that hint.
 */

import { RecoverableError, RemoteRecoverableRPCError } from "./errors.js";

export interface RecoverableRetryOptions {
  /** Maximum number of attempts including the first (default 8). */
  readonly maxRetries?: number;
  /** Bounded exponential backoff when `retryAfterMs` is missing (cap 60s). */
  readonly fallbackBackoffMs?: number;
  /** Injected sleep for tests (default `setTimeout` promise). */
  readonly sleep?: (ms: number) => Promise<void>;
}

function defaultSleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

const FALLBACK_BACKOFF_CAP_MS = 60_000;

function recoverableRetryDelayMs(
  error: unknown,
  attempt: number,
  fallbackBackoffMs: number | undefined,
): number | undefined {
  if (error instanceof RemoteRecoverableRPCError) {
    if (error.retryAfterMs !== undefined) {
      return Math.max(0, error.retryAfterMs);
    }
    if (fallbackBackoffMs !== undefined) {
      return Math.min(FALLBACK_BACKOFF_CAP_MS, fallbackBackoffMs * 2 ** attempt);
    }
    return undefined;
  }
  if (error instanceof RecoverableError) {
    if (error.retryAfterMs !== undefined) {
      return Math.max(0, error.retryAfterMs);
    }
    if (fallbackBackoffMs !== undefined) {
      return Math.min(FALLBACK_BACKOFF_CAP_MS, fallbackBackoffMs * 2 ** attempt);
    }
    return undefined;
  }
  return undefined;
}

/** Runs `op`, retrying on recoverable errors per delay rules above. */
export async function callWithRecoverableRetry<T>(
  op: () => Promise<T>,
  options?: RecoverableRetryOptions,
): Promise<T> {
  const maxRetries = options?.maxRetries ?? 8;
  const sleep = options?.sleep ?? defaultSleep;
  const fallbackBackoffMs = options?.fallbackBackoffMs;
  let attempt = 0;
  for (;;) {
    try {
      return await op();
    } catch (e) {
      const delayMs = recoverableRetryDelayMs(e, attempt, fallbackBackoffMs);
      if (delayMs === undefined || attempt >= maxRetries - 1) {
        throw e;
      }
      await sleep(delayMs);
      attempt += 1;
    }
  }
}
