/**
 * HTTP SSE consumer for POST `/asap/stream` (TS-010, task 4.2).
 *
 * Wire format matches Python `ASAPRequestHandler.handle_stream`: each SSE event is
 * `data: <json envelope>\n\n` (see `src/asap/transport/server.py`).
 */

import { ulid } from "ulid";

import { isRecord } from "./internal/type-guards.js";
import type { Envelope, EnvelopeFor, IsoDateTimeString, TaskStreamPayload } from "./types/envelope.js";
import { narrowEnvelope } from "./types/envelope.js";

/** JSON-RPC method for ASAP HTTP transport. */
export const ASAP_SEND_METHOD = "asap.send" as const;

/** Request / response header for wire version negotiation. */
export const ASAP_VERSION_HEADER = "ASAP-Version" as const;

const DEFAULT_ASAP_VERSION = "2.2";

export type StreamFetch = typeof fetch;

function providerBaseHref(baseUrl: URL | string): string {
  const u = typeof baseUrl === "string" ? new URL(baseUrl) : baseUrl;
  const href = u.href;
  return u.pathname.endsWith("/") ? href : `${href}/`;
}

function asapStreamHref(baseUrl: URL | string): string {
  return new URL("asap/stream", providerBaseHref(baseUrl)).href;
}

function readIsoDateTime(value: unknown): IsoDateTimeString {
  return typeof value === "string" ? value : "";
}

/**
 * Parses a wire JSON object into a loose {@link Envelope}.
 *
 * @throws When required envelope fields are missing or wrong type.
 */
export function envelopeFromWireJson(raw: unknown): Envelope<unknown> {
  if (!isRecord(raw)) {
    throw new Error("ASAP stream: envelope JSON must be an object");
  }
  const id = raw.id;
  const asap_version = raw.asap_version;
  const timestamp = raw.timestamp;
  const sender = raw.sender;
  const recipient = raw.recipient;
  const payload_type = raw.payload_type;
  const payload = raw.payload;
  if (typeof id !== "string") {
    throw new Error("ASAP stream: envelope.id must be a string");
  }
  if (typeof asap_version !== "string") {
    throw new Error("ASAP stream: envelope.asap_version must be a string");
  }
  if (typeof sender !== "string") {
    throw new Error("ASAP stream: envelope.sender must be a string");
  }
  if (typeof recipient !== "string") {
    throw new Error("ASAP stream: envelope.recipient must be a string");
  }
  if (typeof payload_type !== "string") {
    throw new Error("ASAP stream: envelope.payload_type must be a string");
  }
  const correlation_id = optionalStringOrNull(raw.correlation_id);
  const trace_id = optionalStringOrNull(raw.trace_id);
  return {
    id,
    asap_version,
    timestamp: readIsoDateTime(timestamp),
    sender,
    recipient,
    payload_type,
    payload,
    correlation_id,
    trace_id,
    requires_ack: typeof raw.requires_ack === "boolean" ? raw.requires_ack : undefined,
    extensions: isRecord(raw.extensions) ? raw.extensions : raw.extensions === null ? null : undefined,
  };
}

function optionalStringOrNull(value: unknown): string | null | undefined {
  if (value === undefined) {
    return undefined;
  }
  if (value === null) {
    return null;
  }
  if (typeof value === "string") {
    return value;
  }
  return undefined;
}

function isTaskStreamPayload(p: unknown): p is TaskStreamPayload {
  if (!isRecord(p)) {
    return false;
  }
  return typeof p.final === "boolean";
}

function extractSseDataJson(eventBlock: string): string | undefined {
  const dataLines: string[] = [];
  for (const rawLine of eventBlock.split("\n")) {
    const line = rawLine.replace(/\r$/u, "");
    if (line.startsWith("event:")) {
      continue;
    }
    if (line.startsWith("id:")) {
      continue;
    }
    if (line.startsWith("retry:")) {
      continue;
    }
    if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trimStart());
    }
  }
  if (dataLines.length === 0) {
    return undefined;
  }
  return dataLines.join("\n");
}

/**
 * Incrementally parses SSE events from decoded text; each complete event is `block\\n\\n`.
 * Yields JSON strings from `data:` line(s) per event.
 */
async function* sseDataJsonStringsFromReader(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  signal: AbortSignal | undefined,
): AsyncGenerator<string, void, undefined> {
  const decoder = new TextDecoder();
  let carry = "";
  try {
    for (;;) {
      if (signal?.aborted) {
        throw new DOMException("The operation was aborted.", "AbortError");
      }
      const { done, value } = await reader.read();
      if (done) {
        break;
      }
      if (value) {
        carry += decoder.decode(value, { stream: true });
      }
      let sepIndex: number;
      while ((sepIndex = carry.search(/\r?\n\r?\n/u)) !== -1) {
        const block = carry.slice(0, sepIndex);
        carry = carry.slice(sepIndex).replace(/^\r?\n\r?\n/u, "");
        const jsonStr = extractSseDataJson(block);
        if (jsonStr !== undefined && jsonStr.length > 0) {
          yield jsonStr;
        }
      }
    }
    carry += decoder.decode();
    let sepAfter: number;
    while ((sepAfter = carry.search(/\r?\n\r?\n/u)) !== -1) {
      const block = carry.slice(0, sepAfter);
      carry = carry.slice(sepAfter).replace(/^\r?\n\r?\n/u, "");
      const jsonStr = extractSseDataJson(block);
      if (jsonStr !== undefined && jsonStr.length > 0) {
        yield jsonStr;
      }
    }
  } finally {
    await reader.cancel().catch(() => {
      /* ignore */
    });
  }
}

function buildJsonRpcStreamBody(envelope: Envelope<unknown>, requestId: string): { body: string; idempotencyKey: string } {
  const idempotencyKey = ulid();
  const jsonRpcRequest = {
    jsonrpc: "2.0" as const,
    method: ASAP_SEND_METHOD,
    params: {
      envelope: {
        id: envelope.id,
        asap_version: envelope.asap_version,
        timestamp: envelope.timestamp,
        sender: envelope.sender,
        recipient: envelope.recipient,
        payload_type: envelope.payload_type,
        payload: envelope.payload,
        correlation_id: envelope.correlation_id,
        trace_id: envelope.trace_id,
        requires_ack: envelope.requires_ack,
        extensions: envelope.extensions,
      },
      idempotency_key: idempotencyKey,
    },
    id: requestId,
  };
  return { body: JSON.stringify(jsonRpcRequest), idempotencyKey };
}

export interface AsapStreamClientConfig {
  /** Agent base URL (e.g. `https://host:8000`); `/asap/stream` is appended. */
  readonly baseUrl: URL | string;
  readonly fetch?: StreamFetch;
  readonly agentJwt?: string;
  /** Sent as `ASAP-Version` (default `2.2`). */
  readonly asapVersion?: string;
}

export interface AsapStreamClient {
  /**
   * POST the given envelope to `/asap/stream` and yield each SSE `data:` JSON as a
   * {@link EnvelopeFor} `"TaskStream"`. Iteration ends after the chunk with `payload.final === true`.
   */
  stream(
    envelope: Envelope<unknown>,
    options?: { readonly signal?: AbortSignal },
  ): AsyncIterable<EnvelopeFor<"TaskStream">>;
}

/**
 * Creates a minimal HTTP streaming client (no connection pool). For full JSON-RPC
 * batching and retries, combine with transport helpers in later tasks.
 */
export function createAsapStreamClient(config: AsapStreamClientConfig): AsapStreamClient {
  const fetchFn = config.fetch ?? globalThis.fetch.bind(globalThis);
  const asapVersion = config.asapVersion ?? DEFAULT_ASAP_VERSION;
  const streamUrl = asapStreamHref(config.baseUrl);

  return {
    stream(envelope, options) {
      return streamTaskStreamEnvelopes({
        streamUrl,
        envelope,
        fetch: fetchFn,
        signal: options?.signal,
        agentJwt: config.agentJwt,
        asapVersion,
      });
    },
  };
}

export interface StreamTaskStreamEnvelopesOptions {
  /** Full URL to `POST` (e.g. `https://host:8000/asap/stream`). */
  readonly streamUrl: string | URL;
  readonly envelope: Envelope<unknown>;
  readonly fetch?: StreamFetch;
  readonly signal?: AbortSignal;
  readonly agentJwt?: string;
  readonly asapVersion?: string;
}

/**
 * Lower-level helper: POST JSON-RPC to `streamUrl` and parse SSE into TaskStream envelopes.
 */
export async function* streamTaskStreamEnvelopes(
  opts: StreamTaskStreamEnvelopesOptions,
): AsyncGenerator<EnvelopeFor<"TaskStream">, void, undefined> {
  const fetchFn = opts.fetch ?? globalThis.fetch.bind(globalThis);
  const requestId = `req-${ulid()}`;
  const { body, idempotencyKey } = buildJsonRpcStreamBody(opts.envelope, requestId);
  const asapVersion = opts.asapVersion ?? DEFAULT_ASAP_VERSION;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "text/event-stream",
    "X-Idempotency-Key": idempotencyKey,
    [ASAP_VERSION_HEADER]: asapVersion,
  };
  if (opts.agentJwt !== undefined && opts.agentJwt.length > 0) {
    headers.Authorization = `Bearer ${opts.agentJwt}`;
  }

  const response = await fetchFn(typeof opts.streamUrl === "string" ? opts.streamUrl : opts.streamUrl.href, {
    method: "POST",
    headers,
    body,
    signal: opts.signal,
  });

  if (!response.ok || response.body === null) {
    const text = await response.text().catch(() => "");
    throw new Error(`ASAP stream: HTTP ${String(response.status)} ${text.slice(0, 200)}`);
  }

  const reader = response.body.getReader();
  for await (const jsonStr of sseDataJsonStringsFromReader(reader, opts.signal)) {
    let parsed: unknown;
    try {
      parsed = JSON.parse(jsonStr) as unknown;
    } catch {
      throw new Error("ASAP stream: invalid JSON in SSE data line");
    }
    const loose = envelopeFromWireJson(parsed);
    const taskStream = narrowEnvelope(loose, "TaskStream");
    if (taskStream === undefined) {
      throw new Error(`ASAP stream: expected TaskStream payload_type, got ${JSON.stringify(loose.payload_type)}`);
    }
    if (!isTaskStreamPayload(taskStream.payload)) {
      throw new Error("ASAP stream: TaskStream payload missing boolean final");
    }
    yield taskStream;
    if (taskStream.payload.final === true) {
      return;
    }
  }
}
