/**
 * ASAP transport / JSON-RPC error taxonomy (TS-011).
 *
 * Mirrors `src/asap/errors.py`: reserved JSON-RPC band -32059..-32000, remote RPC
 * helpers, and recoverability hints (`recoverable`, `retry_after_ms` in error data).
 */

// --- JSON-RPC application error range (PRD §4.7) ---------------------------------

export const JSON_RPC_ASAP_MIN = -32059;
export const JSON_RPC_ASAP_MAX = -32000;

/** Protocol (-32000..-32009) */
export const RPC_INVALID_STATE = -32000;
export const RPC_MALFORMED_ENVELOPE = -32001;
export const RPC_INVALID_TIMESTAMP = -32002;
export const RPC_INVALID_NONCE = -32003;

/** Routing (-32010..-32019) */
export const RPC_TASK_NOT_FOUND = -32010;
export const RPC_CIRCUIT_OPEN = -32011;
export const RPC_HANDLER_NOT_FOUND = -32012;

/** Capability (-32020..-32029) */
export const RPC_UNSUPPORTED_AUTH_SCHEME = -32020;

/** Execution / transport client (-32030..-32039) */
export const RPC_TASK_ALREADY_COMPLETED = -32030;
export const RPC_THREAD_POOL_EXHAUSTED = -32031;
export const RPC_CONNECTION_ERROR = -32032;
export const RPC_TIMEOUT = -32033;
export const RPC_REMOTE_GENERIC = -32034;

/** Resource (-32040..-32049) */
export const RPC_RESOURCE_EXHAUSTED = -32040;

/** Security (-32050..-32059) */
export const RPC_WEBHOOK_URL_REJECTED = -32050;
export const RPC_AGENT_REVOKED = -32051;
export const RPC_SIGNATURE_VERIFICATION = -32052;

export function isAsapJsonRpcCode(code: number): boolean {
  return code >= JSON_RPC_ASAP_MIN && code <= JSON_RPC_ASAP_MAX;
}

/** Maps wire JSON-RPC code to the ASAP slot used on typed errors (falls back to {@link RPC_REMOTE_GENERIC}). */
export function clampAsapRpcSlot(wireJsonRpcCode: number): number {
  return isAsapJsonRpcCode(wireJsonRpcCode) ? wireJsonRpcCode : RPC_REMOTE_GENERIC;
}

export interface ConstraintViolation {
  readonly field: string;
  readonly operator: string;
  readonly message: string;
}

export class RecoverableError extends Error {
  readonly code: string;
  readonly retryAfterMs?: number;
  readonly violations?: readonly ConstraintViolation[];
  /** ASAP JSON-RPC slot when this error maps to the reserved band. */
  readonly rpcCode?: number;
  readonly details?: Readonly<Record<string, unknown>>;

  constructor(opts: {
    message?: string;
    code: string;
    retryAfterMs?: number;
    violations?: readonly ConstraintViolation[];
    rpcCode?: number;
    details?: Record<string, unknown>;
  }) {
    super(opts.message ?? opts.code);
    this.name = "RecoverableError";
    this.code = opts.code;
    this.retryAfterMs = opts.retryAfterMs;
    this.violations = opts.violations;
    this.rpcCode = opts.rpcCode;
    this.details = opts.details;
  }
}

export class FatalError extends Error {
  readonly taxonomyCode: string;
  readonly rpcCode: number;
  readonly details: Readonly<Record<string, unknown>>;
  readonly retryAfterMs?: number;
  readonly alternativeAgents?: readonly string[];
  readonly fallbackAction?: string;

  constructor(opts: {
    taxonomyCode: string;
    message: string;
    rpcCode: number;
    details?: Record<string, unknown>;
    retryAfterMs?: number;
    alternativeAgents?: readonly string[];
    fallbackAction?: string;
  }) {
    super(opts.message);
    this.name = "FatalError";
    this.taxonomyCode = opts.taxonomyCode;
    this.rpcCode = opts.rpcCode;
    this.details = opts.details ?? {};
    this.retryAfterMs = opts.retryAfterMs;
    this.alternativeAgents = opts.alternativeAgents;
    this.fallbackAction = opts.fallbackAction;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export interface PoppedAsapRemoteMeta {
  readonly taxonomyCode: string;
  readonly details: Record<string, unknown>;
  readonly retryAfterMs: number | undefined;
  readonly alternativeAgents: string[] | undefined;
  readonly fallbackAction: string | undefined;
}

/**
 * Extract taxonomy and recovery hints from JSON-RPC `error.data` (mirrors `_pop_remote_meta`).
 */
export function popAsapRemoteErrorMeta(data: unknown): PoppedAsapRemoteMeta {
  const raw = isRecord(data) ? { ...data } : {};
  let taxonomy = "asap:rpc/remote_error";
  if (typeof raw.asap_taxonomy_code === "string") {
    taxonomy = raw.asap_taxonomy_code;
  }
  delete raw.asap_taxonomy_code;
  delete raw.recoverable;

  let retryAfterMs: number | undefined;
  if (raw.retry_after_ms !== undefined && raw.retry_after_ms !== null) {
    const n = Number(raw.retry_after_ms);
    retryAfterMs = Number.isFinite(n) ? n : undefined;
  }
  delete raw.retry_after_ms;

  let alternativeAgents: string[] | undefined;
  if (Array.isArray(raw.alternative_agents)) {
    alternativeAgents = raw.alternative_agents.filter((a): a is string => typeof a === "string");
  }
  delete raw.alternative_agents;

  let fallbackAction: string | undefined;
  if (raw.fallback_action !== undefined && raw.fallback_action !== null) {
    fallbackAction = String(raw.fallback_action);
  }
  delete raw.fallback_action;

  delete raw.rpc_code;

  const taxonomyAlt = raw.code;
  delete raw.code;
  if (typeof taxonomyAlt === "string" && taxonomyAlt.startsWith("asap:")) {
    taxonomy = taxonomyAlt;
  }

  return {
    taxonomyCode: taxonomy,
    details: raw,
    retryAfterMs,
    alternativeAgents: alternativeAgents?.length ? alternativeAgents : undefined,
    fallbackAction,
  };
}

/** Fatal JSON-RPC error from a remote ASAP peer (client-side). */
export class RemoteFatalRPCError extends FatalError {
  readonly jsonRpcCode: number;

  constructor(opts: {
    wireJsonRpcCode: number;
    message: string;
    taxonomyCode?: string;
    details?: Record<string, unknown>;
    retryAfterMs?: number;
    alternativeAgents?: readonly string[];
    fallbackAction?: string;
  }) {
    const slot = clampAsapRpcSlot(opts.wireJsonRpcCode);
    super({
      taxonomyCode: opts.taxonomyCode ?? "asap:rpc/remote_error",
      message: opts.message,
      rpcCode: slot,
      details: opts.details ?? {},
      retryAfterMs: opts.retryAfterMs,
      alternativeAgents: opts.alternativeAgents,
      fallbackAction: opts.fallbackAction,
    });
    this.name = "RemoteFatalRPCError";
    this.jsonRpcCode = opts.wireJsonRpcCode;
  }

  static fromJsonRpc(wireCode: number, message: string, data: unknown): RemoteFatalRPCError {
    const meta = popAsapRemoteErrorMeta(data);
    return new RemoteFatalRPCError({
      wireJsonRpcCode: wireCode,
      message,
      taxonomyCode: meta.taxonomyCode,
      details: meta.details,
      retryAfterMs: meta.retryAfterMs,
      alternativeAgents: meta.alternativeAgents,
      fallbackAction: meta.fallbackAction,
    });
  }
}

/** Recoverable JSON-RPC error from a remote ASAP peer (client-side). */
export class RemoteRecoverableRPCError extends RecoverableError {
  readonly jsonRpcCode: number;
  readonly remoteDetails: Readonly<Record<string, unknown>>;

  constructor(opts: {
    wireJsonRpcCode: number;
    message: string;
    taxonomyCode?: string;
    retryAfterMs?: number;
    details?: Record<string, unknown>;
    alternativeAgents?: readonly string[];
    fallbackAction?: string;
  }) {
    const slot = clampAsapRpcSlot(opts.wireJsonRpcCode);
    super({
      code: opts.taxonomyCode ?? "asap:rpc/remote_recoverable_error",
      message: opts.message,
      retryAfterMs: opts.retryAfterMs,
      rpcCode: slot,
      details: opts.details,
    });
    this.name = "RemoteRecoverableRPCError";
    this.jsonRpcCode = opts.wireJsonRpcCode;
    this.remoteDetails = opts.details ?? {};
  }

  static fromJsonRpc(wireCode: number, message: string, data: unknown): RemoteRecoverableRPCError {
    const meta = popAsapRemoteErrorMeta(data);
    return new RemoteRecoverableRPCError({
      wireJsonRpcCode: wireCode,
      message,
      taxonomyCode: meta.taxonomyCode,
      retryAfterMs: meta.retryAfterMs,
      details: meta.details,
      alternativeAgents: meta.alternativeAgents,
      fallbackAction: meta.fallbackAction,
    });
  }
}

/** Alias matching Python `ASAPRemoteError`. */
export type AsapRemoteError = RemoteFatalRPCError;

/**
 * Build a typed remote exception from JSON-RPC `error.code` / `message` / `data`,
 * using `data.recoverable === true` for {@link RemoteRecoverableRPCError}.
 */
export function remoteRpcErrorFromJson(
  rpcCode: number,
  message: string,
  data: unknown,
): RemoteFatalRPCError | RemoteRecoverableRPCError {
  const d = isRecord(data) ? data : {};
  if (d.recoverable === true) {
    return RemoteRecoverableRPCError.fromJsonRpc(rpcCode, message, d);
  }
  return RemoteFatalRPCError.fromJsonRpc(rpcCode, message, d);
}

/** JSON-RPC error object shape (`error` field). */
export interface JsonRpcErrorWire {
  readonly code: number;
  readonly message: string;
  readonly data?: unknown;
}

export function remoteRpcErrorFromJsonRpcError(err: JsonRpcErrorWire): RemoteFatalRPCError | RemoteRecoverableRPCError {
  const data = isRecord(err.data) ? err.data : undefined;
  return remoteRpcErrorFromJson(Number(err.code), String(err.message ?? ""), data);
}
