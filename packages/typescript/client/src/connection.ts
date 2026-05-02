/**
 * Agent connection lifecycle: register, status, revoke, reactivate, request-capability (TS-004, TS-005, ESC-004).
 *
 * @see `src/asap/transport/agent_routes.py`, `src/asap/transport/capability_routes.py`
 */

import type { AgentContext, AgentMode, HostContext } from "./identity.js";
import { isRecord } from "./internal/type-guards.js";

export type ConnectionFetch = typeof fetch;

/** JWT `aud` must match the provider’s expected audience (often the gateway base URL). */
export interface ConnectionJwtOptions {
  readonly audience: string;
  readonly fetch?: ConnectionFetch;
  readonly signal?: AbortSignal;
}

export interface ConnectAgentOptions extends ConnectionJwtOptions {
  readonly approvalMethod?: "device_authorization" | "ciba";
  readonly agentControlsBrowser?: boolean;
}

export interface ConnectAgentResult {
  readonly agentId: string;
  readonly hostId: string;
  readonly status: string;
  readonly approval?: unknown;
  readonly agentCapabilityGrants?: unknown;
}

export interface AgentLifecycleInfo {
  readonly mode?: string;
  readonly session_ttl?: number | null;
  readonly max_lifetime?: number | null;
  readonly absolute_lifetime?: number | null;
  readonly created_at?: string;
  readonly activated_at?: string | null;
  readonly last_used_at?: string | null;
}

export interface AgentCapabilityGrantSummary {
  readonly capability: string;
  readonly status?: string;
  readonly reason?: string;
  readonly constraints?: unknown;
  readonly granted_by?: string;
  readonly expires_at?: string;
}

export interface AgentStatusResult {
  readonly agentId: string;
  readonly hostId: string;
  readonly status: string;
  readonly capabilities: AgentCapabilityGrantSummary[];
  readonly lifecycle?: AgentLifecycleInfo;
  readonly approvalStatus?: string;
  readonly approval?: unknown;
  readonly denyReason?: string;
}

export interface DisconnectAgentResult {
  readonly agentId: string;
  readonly status: string;
}

export interface ReactivateAgentResult {
  readonly agentId: string;
  readonly status: string;
  readonly capabilities: AgentCapabilityGrantSummary[];
}

export type CapabilityRequestSpec = string | { readonly name: string; readonly constraints?: Record<string, unknown> };

/** Parsed JSON body from a successful `POST /asap/agent/request-capability` response. */
export interface RequestCapabilityResult {
  readonly status?: string;
  readonly [key: string]: unknown;
}

function asapUrl(provider: URL, relativePath: string): string {
  const base = provider.pathname.endsWith("/") ? provider.href : `${provider.href}/`;
  return new URL(relativePath.replace(/^\//u, ""), base).href;
}

function httpErrorDetailFromBodyText(text: string): string {
  try {
    const parsed: unknown = JSON.parse(text);
    if (isRecord(parsed) && typeof parsed.detail === "string") {
      return parsed.detail;
    }
    if (isRecord(parsed) && typeof parsed.error === "string") {
      return parsed.error;
    }
  } catch {
    /* ignore */
  }
  return text.slice(0, 400);
}

function parseGrant(raw: unknown, index: number): AgentCapabilityGrantSummary {
  if (!isRecord(raw)) throw new Error(`capabilities[${String(index)}]: expected object`);
  const capability = raw.capability;
  if (typeof capability !== "string") throw new Error(`capabilities[${String(index)}]: missing capability`);
  return {
    capability,
    status: typeof raw.status === "string" ? raw.status : undefined,
    reason: typeof raw.reason === "string" ? raw.reason : undefined,
    constraints: raw.constraints,
    granted_by: typeof raw.granted_by === "string" ? raw.granted_by : undefined,
    expires_at: typeof raw.expires_at === "string" ? raw.expires_at : undefined,
  };
}

function parseLifecycle(raw: unknown): AgentLifecycleInfo | undefined {
  if (!isRecord(raw)) return undefined;
  return {
    mode: typeof raw.mode === "string" ? raw.mode : undefined,
    session_ttl: typeof raw.session_ttl === "number" ? raw.session_ttl : raw.session_ttl === null ? null : undefined,
    max_lifetime: typeof raw.max_lifetime === "number" ? raw.max_lifetime : raw.max_lifetime === null ? null : undefined,
    absolute_lifetime:
      typeof raw.absolute_lifetime === "number"
        ? raw.absolute_lifetime
        : raw.absolute_lifetime === null
          ? null
          : undefined,
    created_at: typeof raw.created_at === "string" ? raw.created_at : undefined,
    activated_at: typeof raw.activated_at === "string" ? raw.activated_at : raw.activated_at === null ? null : undefined,
    last_used_at: typeof raw.last_used_at === "string" ? raw.last_used_at : raw.last_used_at === null ? null : undefined,
  };
}

function normalizeCapabilitySpecs(requested: readonly CapabilityRequestSpec[]): unknown[] {
  const out: unknown[] = [];
  for (const item of requested) {
    if (typeof item === "string") {
      out.push(item);
    } else {
      out.push({ name: item.name, ...(item.constraints !== undefined ? { constraints: item.constraints } : {}) });
    }
  }
  return out;
}

/**
 * Register the agent with the provider (`POST /asap/agent/register`) using a Host JWT that includes
 * the agent public key (same shape as the Python transport).
 */
export async function connectAgent(
  provider: URL,
  host: HostContext,
  agent: AgentContext,
  capabilities: string[],
  mode: AgentMode,
  options: ConnectAgentOptions,
): Promise<ConnectAgentResult> {
  const token = await host.signHostJwt({
    aud: options.audience,
    agentPublicKey: agent.publicJwk,
  });
  const body: Record<string, unknown> = {
    capabilities,
    mode,
  };
  if (options.approvalMethod !== undefined) {
    body.approval_method = options.approvalMethod;
  }
  if (options.agentControlsBrowser === true) {
    body.agent_controls_browser = true;
  }
  const fetchFn = options.fetch ?? globalThis.fetch;
  const res = await fetchFn(asapUrl(provider, "asap/agent/register"), {
    method: "POST",
    signal: options.signal,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  });
  const text = await res.text();
  let parsed: unknown;
  try {
    parsed = text.length === 0 ? {} : JSON.parse(text);
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    throw new Error(`connectAgent: invalid JSON (${msg})`);
  }
  if (!res.ok) {
    throw new Error(`connectAgent failed: HTTP ${String(res.status)} ${httpErrorDetailFromBodyText(text)}`);
  }
  if (!isRecord(parsed)) throw new Error("connectAgent: expected object response");
  const agentId = parsed.agent_id;
  const hostId = parsed.host_id;
  const status = parsed.status;
  if (typeof agentId !== "string" || typeof hostId !== "string" || typeof status !== "string") {
    throw new Error("connectAgent: missing agent_id, host_id, or status");
  }
  return {
    agentId,
    hostId,
    status,
    approval: parsed.approval,
    agentCapabilityGrants: parsed.agent_capability_grants,
  };
}

/**
 * Revoke an agent session (`POST /asap/agent/revoke`).
 */
export async function disconnectAgent(
  provider: URL,
  host: HostContext,
  agentId: string,
  options: ConnectionJwtOptions,
): Promise<DisconnectAgentResult> {
  const token = await host.signHostJwt({ aud: options.audience });
  const fetchFn = options.fetch ?? globalThis.fetch;
  const res = await fetchFn(asapUrl(provider, "asap/agent/revoke"), {
    method: "POST",
    signal: options.signal,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ agent_id: agentId }),
  });
  const text = await res.text();
  let parsed: unknown;
  try {
    parsed = text.length === 0 ? {} : JSON.parse(text);
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    throw new Error(`disconnectAgent: invalid JSON (${msg})`);
  }
  if (!res.ok) {
    throw new Error(`disconnectAgent failed: HTTP ${String(res.status)} ${httpErrorDetailFromBodyText(text)}`);
  }
  if (!isRecord(parsed)) throw new Error("disconnectAgent: expected object response");
  const aid = parsed.agent_id;
  const status = parsed.status;
  if (typeof aid !== "string" || typeof status !== "string") {
    throw new Error("disconnectAgent: missing agent_id or status");
  }
  return { agentId: aid, status };
}

/**
 * Poll agent status and grants (`GET /asap/agent/status`).
 */
export async function agentStatus(
  provider: URL,
  host: HostContext,
  agentId: string,
  options: ConnectionJwtOptions,
): Promise<AgentStatusResult> {
  const token = await host.signHostJwt({ aud: options.audience });
  const url = new URL(asapUrl(provider, "asap/agent/status"));
  url.searchParams.set("agent_id", agentId);
  const fetchFn = options.fetch ?? globalThis.fetch;
  const res = await fetchFn(url.href, {
    method: "GET",
    signal: options.signal,
    headers: { Accept: "application/json", Authorization: `Bearer ${token}` },
  });
  const text = await res.text();
  let parsed: unknown;
  try {
    parsed = text.length === 0 ? {} : JSON.parse(text);
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    throw new Error(`agentStatus: invalid JSON (${msg})`);
  }
  if (!res.ok) {
    throw new Error(`agentStatus failed: HTTP ${String(res.status)} ${httpErrorDetailFromBodyText(text)}`);
  }
  if (!isRecord(parsed)) throw new Error("agentStatus: expected object response");
  const aid = parsed.agent_id;
  const hid = parsed.host_id;
  const status = parsed.status;
  if (typeof aid !== "string" || typeof hid !== "string" || typeof status !== "string") {
    throw new Error("agentStatus: missing agent_id, host_id, or status");
  }
  const capsRaw = parsed.capabilities;
  const capabilities = Array.isArray(capsRaw) ? capsRaw.map((g, i) => parseGrant(g, i)) : [];
  return {
    agentId: aid,
    hostId: hid,
    status,
    capabilities,
    lifecycle: parseLifecycle(parsed.lifecycle),
    approvalStatus: typeof parsed.approval_status === "string" ? parsed.approval_status : undefined,
    approval: parsed.approval,
    denyReason: typeof parsed.deny_reason === "string" ? parsed.deny_reason : undefined,
  };
}

/**
 * Reactivate an expired agent (`POST /asap/agent/reactivate`) — Host JWT.
 */
export async function reactivateAgent(
  provider: URL,
  host: HostContext,
  agentId: string,
  options: ConnectionJwtOptions,
): Promise<ReactivateAgentResult> {
  const token = await host.signHostJwt({ aud: options.audience });
  const fetchFn = options.fetch ?? globalThis.fetch;
  const res = await fetchFn(asapUrl(provider, "asap/agent/reactivate"), {
    method: "POST",
    signal: options.signal,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ agent_id: agentId }),
  });
  const text = await res.text();
  let parsed: unknown;
  try {
    parsed = text.length === 0 ? {} : JSON.parse(text);
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    throw new Error(`reactivateAgent: invalid JSON (${msg})`);
  }
  if (!res.ok) {
    throw new Error(`reactivateAgent failed: HTTP ${String(res.status)} ${httpErrorDetailFromBodyText(text)}`);
  }
  if (!isRecord(parsed)) throw new Error("reactivateAgent: expected object response");
  const aid = parsed.agent_id;
  const status = parsed.status;
  if (typeof aid !== "string" || typeof status !== "string") {
    throw new Error("reactivateAgent: missing agent_id or status");
  }
  const capsRaw = parsed.capabilities;
  const capabilities = Array.isArray(capsRaw) ? capsRaw.map((g, i) => parseGrant(g, i)) : [];
  return { agentId: aid, status, capabilities };
}

/**
 * Request additional capabilities for an existing agent (`POST /asap/agent/request-capability`) — Agent JWT.
 *
 * @remarks Aligns with ESC-001 / ESC-004; requires a provider that exposes this route.
 */
export async function requestCapability(
  provider: URL,
  agent: AgentContext,
  capabilities: CapabilityRequestSpec[],
  options: ConnectionJwtOptions,
): Promise<RequestCapabilityResult> {
  const names = capabilities.map((c) => (typeof c === "string" ? c : c.name));
  const token = await agent.signAgentJwt({ aud: options.audience, capabilities: names });
  const body = JSON.stringify({ capabilities: normalizeCapabilitySpecs(capabilities) });
  const fetchFn = options.fetch ?? globalThis.fetch;
  const res = await fetchFn(asapUrl(provider, "asap/agent/request-capability"), {
    method: "POST",
    signal: options.signal,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body,
  });
  const text = await res.text();
  let parsed: unknown;
  try {
    parsed = text.length === 0 ? null : JSON.parse(text);
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    throw new Error(`requestCapability: invalid JSON (${msg})`);
  }
  if (!res.ok) {
    throw new Error(`requestCapability failed: HTTP ${String(res.status)} ${httpErrorDetailFromBodyText(text)}`);
  }
  if (!isRecord(parsed)) {
    throw new Error("requestCapability: expected JSON object response body");
  }
  return parsed as RequestCapabilityResult;
}
