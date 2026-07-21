/**
 * Gateway capability list / describe / execute helpers.
 *
 * @see `src/asap/transport/capability_routes.py`
 */

import { RecoverableError, type ConstraintViolation } from "./errors.js";
import { isRecord } from "./internal/type-guards.js";

export interface ListCapabilitiesItem {
  readonly name: string;
  readonly description: string;
  readonly location?: string;
  readonly grant_status?: string | null;
}

export interface ListCapabilitiesResult {
  readonly capabilities: ListCapabilitiesItem[];
  readonly next_cursor?: number;
}

export interface DescribeCapabilityResult {
  readonly name: string;
  readonly description: string;
  readonly input_schema?: unknown;
  readonly output_schema?: unknown;
  readonly location?: string;
}

export type CapabilityFetch = typeof fetch;

export interface CapabilityRequestOptions {
  readonly fetch?: CapabilityFetch;
  readonly signal?: AbortSignal;
  /** When set, sends `Authorization: Bearer &lt;token&gt;` (Agent JWT for execute; optional for list/describe). */
  readonly agentJwt?: string;
}

export interface ListCapabilitiesOptions extends CapabilityRequestOptions {
  readonly query?: string;
  readonly cursor?: number;
  readonly limit?: number;
}

export interface ExecuteCapabilityOptions extends CapabilityRequestOptions {}

/** Base URL with trailing slash for safe relative resolution of `asap/...` paths. */
function providerBaseHref(provider: URL): string {
  const href = provider.href;
  return provider.pathname.endsWith("/") ? href : `${href}/`;
}

function capabilityEndpoint(provider: URL, path: string): string {
  return new URL(path.replace(/^\//u, ""), providerBaseHref(provider)).href;
}

function authHeaders(agentJwt: string | undefined): HeadersInit {
  const headers: Record<string, string> = {};
  if (agentJwt !== undefined && agentJwt.length > 0) {
    headers.Authorization = `Bearer ${agentJwt}`;
  }
  return headers;
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

function jsonRpcErrorToError(error: unknown): Error {
  if (!isRecord(error)) {
    return new Error(String(error));
  }
  const code = error.code;
  const message = typeof error.message === "string" ? error.message : JSON.stringify(error);
  const err = new Error(message);
  err.name = "JsonRpcError";
  if (typeof code === "number") {
    (err as Error & { code?: number }).code = code;
  }
  return err;
}

function parseViolation(raw: unknown, index: number): ConstraintViolation {
  if (!isRecord(raw)) {
    throw new Error(`violations[${String(index)}]: expected object`);
  }
  const field = raw.field;
  const operator = raw.operator;
  const message = raw.message;
  if (typeof field !== "string" || typeof operator !== "string" || typeof message !== "string") {
    throw new Error(`violations[${String(index)}]: field, operator, and message must be strings`);
  }
  return { field, operator, message };
}

function throwForExecuteFailure(status: number, payload: unknown): never {
  if (
    status === 403 &&
    isRecord(payload) &&
    payload.error === "constraint_violated" &&
    Array.isArray(payload.violations)
  ) {
    const violations = payload.violations.map((v, i) => parseViolation(v, i));
    const cap = payload.capability;
    const capLabel = typeof cap === "string" ? cap : "";
    throw new RecoverableError({
      code: "CONSTRAINT_VIOLATED",
      message: `constraint violated for capability ${capLabel}`,
      violations,
    });
  }
  const detail =
    isRecord(payload) && typeof payload.detail === "string"
      ? payload.detail
      : isRecord(payload) && typeof payload.error === "string"
        ? payload.error
        : JSON.stringify(payload);
  throw new Error(`capability execute failed: HTTP ${String(status)} ${detail}`);
}

/**
 * List capabilities exposed by the provider (`GET /asap/capability/list`).
 */
export async function listCapabilities(
  provider: URL,
  options?: ListCapabilitiesOptions,
): Promise<ListCapabilitiesResult> {
  const url = new URL(capabilityEndpoint(provider, "asap/capability/list"));
  if (options?.query !== undefined) url.searchParams.set("query", options.query);
  if (options?.cursor !== undefined) url.searchParams.set("cursor", String(options.cursor));
  if (options?.limit !== undefined) url.searchParams.set("limit", String(options.limit));

  const fetchFn = options?.fetch ?? globalThis.fetch;
  const res = await fetchFn(url.href, {
    method: "GET",
    headers: { Accept: "application/json", ...authHeaders(options?.agentJwt) },
    signal: options?.signal,
  });
  const text = await res.text();
  let parsed: unknown;
  try {
    parsed = text.length === 0 ? {} : JSON.parse(text);
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    throw new Error(`capability list: invalid JSON (${msg})`);
  }
  if (!res.ok) {
    throw new Error(`capability list failed: HTTP ${String(res.status)} ${text.slice(0, 200)}`);
  }
  const unwrapped = parseJsonRpcResult(parsed);
  if (!isRecord(unwrapped) || !Array.isArray(unwrapped.capabilities)) {
    throw new Error("capability list: expected capabilities array");
  }
  const caps = unwrapped.capabilities.map((item, i) => {
    if (!isRecord(item)) throw new Error(`capabilities[${String(i)}]: expected object`);
    const name = item.name;
    const description = item.description;
    if (typeof name !== "string" || typeof description !== "string") {
      throw new Error(`capabilities[${String(i)}]: name and description must be strings`);
    }
    const entry: ListCapabilitiesItem = {
      name,
      description,
      location: typeof item.location === "string" ? item.location : undefined,
      grant_status:
        item.grant_status === null || typeof item.grant_status === "string" ? item.grant_status : undefined,
    };
    return entry;
  });
  const next = unwrapped.next_cursor;
  return {
    capabilities: caps,
    next_cursor: typeof next === "number" ? next : undefined,
  };
}

/**
 * Describe a single capability (`GET /asap/capability/describe?name=`).
 */
export async function describeCapability(
  provider: URL,
  name: string,
  options?: CapabilityRequestOptions,
): Promise<DescribeCapabilityResult> {
  const url = new URL(capabilityEndpoint(provider, "asap/capability/describe"));
  url.searchParams.set("name", name);

  const fetchFn = options?.fetch ?? globalThis.fetch;
  const res = await fetchFn(url.href, {
    method: "GET",
    headers: { Accept: "application/json", ...authHeaders(options?.agentJwt) },
    signal: options?.signal,
  });
  const text = await res.text();
  let parsed: unknown;
  try {
    parsed = text.length === 0 ? {} : JSON.parse(text);
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    throw new Error(`capability describe: invalid JSON (${msg})`);
  }
  if (!res.ok) {
    throw new Error(`capability describe failed: HTTP ${String(res.status)} ${text.slice(0, 200)}`);
  }
  const unwrapped = parseJsonRpcResult(parsed);
  if (!isRecord(unwrapped)) {
    throw new Error("capability describe: expected object");
  }
  const n = unwrapped.name;
  const description = unwrapped.description;
  if (typeof n !== "string" || typeof description !== "string") {
    throw new Error("capability describe: name and description must be strings");
  }
  return {
    name: n,
    description,
    input_schema: unwrapped.input_schema,
    output_schema: unwrapped.output_schema,
    location: typeof unwrapped.location === "string" ? unwrapped.location : undefined,
  };
}

/**
 * Execute a capability (`POST /asap/capability/execute`) with optional Agent JWT.
 *
 * Request body matches the Python gateway: `{ capability, arguments }`.
 * Responses may be plain JSON or JSON-RPC 2.0; both are normalized.
 */
export async function executeCapability(
  provider: URL,
  name: string,
  args: Record<string, unknown>,
  options?: ExecuteCapabilityOptions,
): Promise<unknown> {
  const url = capabilityEndpoint(provider, "asap/capability/execute");
  const body = JSON.stringify({ capability: name, arguments: args });
  const fetchFn = options?.fetch ?? globalThis.fetch;
  const res = await fetchFn(url, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...authHeaders(options?.agentJwt),
    },
    body,
    signal: options?.signal,
  });
  const text = await res.text();
  let parsed: unknown;
  try {
    parsed = text.length === 0 ? null : JSON.parse(text);
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    throw new Error(`capability execute: invalid JSON (${msg})`);
  }
  if (!res.ok) {
    throwForExecuteFailure(res.status, parsed);
  }
  return parseJsonRpcResult(parsed);
}
