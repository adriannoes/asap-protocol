import { ASAP_SEND_METHOD, ASAP_VERSION_HEADER } from "@asap-protocol/client";

const DEFAULT_ASAP_VERSION = "2.2";

export type SendAsapFetch = typeof fetch;

export interface SendAsapEnvelopeOptions {
  readonly fetch?: SendAsapFetch;
  readonly signal?: AbortSignal;
  /** When set, sends `Authorization: Bearer <token>`. */
  readonly agentJwt?: string;
  /** Sent as `ASAP-Version` (default `2.2`). */
  readonly asapVersion?: string;
}

/** Base URL with trailing slash for safe relative resolution of `asap/...` paths. */
function providerBaseHref(provider: URL): string {
  const href = provider.href;
  return provider.pathname.endsWith("/") ? href : `${href}/`;
}

function asapSendHref(provider: URL): string {
  return new URL("asap", providerBaseHref(provider)).href;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function jsonRpcErrorToError(error: unknown): Error {
  if (!isRecord(error)) {
    return new Error(String(error));
  }
  const message = typeof error.message === "string" ? error.message : JSON.stringify(error);
  const err = new Error(message);
  err.name = "JsonRpcError";
  if (typeof error.code === "number") {
    (err as Error & { code?: number }).code = error.code;
  }
  return err;
}

function parseJsonRpcResult(payload: unknown): unknown {
  if (!isRecord(payload)) {
    return payload;
  }
  if (payload.jsonrpc !== "2.0") {
    return payload;
  }
  if (payload.error !== undefined && payload.error !== null) {
    throw jsonRpcErrorToError(payload.error);
  }
  return payload.result;
}

function normalizeEnvelopeForSend(envelope: Record<string, unknown>): Record<string, unknown> {
  return {
    ...envelope,
    id: typeof envelope.id === "string" ? envelope.id : crypto.randomUUID(),
    timestamp: typeof envelope.timestamp === "string" ? envelope.timestamp : new Date().toISOString(),
  };
}

function buildJsonRpcSendBody(envelope: Record<string, unknown>): { body: string; idempotencyKey: string } {
  const requestId = crypto.randomUUID();
  const idempotencyKey = crypto.randomUUID();
  const jsonRpcRequest = {
    jsonrpc: "2.0" as const,
    method: ASAP_SEND_METHOD,
    params: {
      envelope,
      idempotency_key: idempotencyKey,
    },
    id: requestId,
  };
  return { body: JSON.stringify(jsonRpcRequest), idempotencyKey };
}

/**
 * POST a JSON-RPC `asap.send` request to the provider's `/asap` endpoint.
 *
 * @throws When HTTP status is not ok or the JSON-RPC response contains an error.
 */
export async function sendAsapEnvelope(
  provider: URL,
  envelope: Record<string, unknown>,
  options?: SendAsapEnvelopeOptions,
): Promise<unknown> {
  const fetchFn = options?.fetch ?? globalThis.fetch.bind(globalThis);
  const asapVersion = options?.asapVersion ?? DEFAULT_ASAP_VERSION;
  const wireEnvelope = normalizeEnvelopeForSend(envelope);
  const { body, idempotencyKey } = buildJsonRpcSendBody(wireEnvelope);

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
    "X-Idempotency-Key": idempotencyKey,
    [ASAP_VERSION_HEADER]: asapVersion,
  };
  if (options?.agentJwt !== undefined && options.agentJwt.length > 0) {
    headers.Authorization = `Bearer ${options.agentJwt}`;
  }

  const response = await fetchFn(asapSendHref(provider), {
    method: "POST",
    headers,
    body,
    signal: options?.signal,
  });

  const text = await response.text();
  let parsed: unknown;
  try {
    parsed = text.length === 0 ? {} : JSON.parse(text);
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    throw new Error(`asap.send: invalid JSON (${msg})`);
  }

  if (!response.ok) {
    throw new Error(`asap.send failed: HTTP ${String(response.status)} ${text.slice(0, 200)}`);
  }

  return parseJsonRpcResult(parsed);
}
