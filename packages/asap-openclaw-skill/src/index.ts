/**
 * ASAP Protocol OpenClaw Skill
 *
 * Registers the `asap_invoke` tool so OpenClaw agents can invoke ASAP agents by URN.
 * Resolves URNs via the Lite Registry and sends JSON-RPC task.request to agent endpoints.
 */

import { Type } from "@sinclair/typebox";

const DEFAULT_REGISTRY_URL =
  process.env.ASAP_REGISTRY_URL ||
  "https://asap-protocol.github.io/registry/registry.json";

const DEFAULT_REQUEST_TIMEOUT_MS = 30_000;

function getTimeoutMs(): number {
  const raw = process.env.ASAP_REQUEST_TIMEOUT_MS;
  if (!raw) return DEFAULT_REQUEST_TIMEOUT_MS;
  const n = parseInt(raw, 10);
  return Number.isFinite(n) && n > 0 ? n : DEFAULT_REQUEST_TIMEOUT_MS;
}

const ASAP_PROTOCOL_VERSION = "0.1";
const ASAP_JSONRPC_METHOD = "asap.send";
const SENDER_URN = "urn:asap:agent:openclaw-skill";

function generateId(): string {
  return typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
    ? crypto.randomUUID()
    : Date.now().toString(36) + Math.random().toString(36).slice(2);
}

interface RegistryEntry {
  id: string;
  name?: string;
  endpoints?: {
    http?: string;
    manifest?: string;
  };
}

interface RegistryResponse {
  agents?: RegistryEntry[];
}

export async function fetchRegistry(registryUrl: string): Promise<RegistryEntry[]> {
  const timeoutMs = getTimeoutMs();
  const res = await fetch(registryUrl, {
    signal: AbortSignal.timeout(timeoutMs),
  });
  if (!res.ok) {
    throw new Error(`Registry fetch failed: ${res.status} ${res.statusText}`);
  }
  const data = (await res.json()) as RegistryResponse;
  return data.agents ?? [];
}

export function findEntryByUrn(agents: RegistryEntry[], urn: string): RegistryEntry | null {
  return agents.find((a) => a.id === urn) ?? null;
}

export function getHttpEndpoint(entry: RegistryEntry): string {
  const http = entry.endpoints?.http;
  if (!http) {
    throw new Error(`Agent ${entry.id} has no HTTP endpoint`);
  }
  return http;
}

export async function invokeAsapAgent(
  httpEndpoint: string,
  urn: string,
  skillId: string,
  input: Record<string, unknown>,
  authToken?: string
): Promise<unknown> {
  const envelope = {
    asap_version: ASAP_PROTOCOL_VERSION,
    sender: SENDER_URN,
    recipient: urn,
    payload_type: "task.request",
    payload: {
      conversation_id: generateId(),
      skill_id: skillId,
      input: input ?? {},
    },
    correlation_id: generateId(),
  };

  const jsonRpcRequest = {
    jsonrpc: "2.0",
    method: ASAP_JSONRPC_METHOD,
    params: { envelope },
    id: generateId(),
  };

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (authToken) {
    headers["Authorization"] = `Bearer ${authToken}`;
  }

  const timeoutMs = getTimeoutMs();
  const res = await fetch(httpEndpoint, {
    method: "POST",
    headers,
    body: JSON.stringify(jsonRpcRequest),
    signal: AbortSignal.timeout(timeoutMs),
  });

  if (!res.ok) {
    throw new Error(`ASAP agent request failed: ${res.status} ${res.statusText}`);
  }

  const json = (await res.json()) as {
    jsonrpc?: string;
    result?: { envelope?: { payload?: { result?: unknown } } };
    error?: { code: number; message: string; data?: unknown };
  };

  if (json.error) {
    throw new Error(`ASAP agent error: ${json.error.message}`);
  }

  const resultEnvelope = json.result?.envelope;
  const payload = resultEnvelope?.payload as { result?: unknown } | undefined;
  return payload?.result ?? resultEnvelope ?? json.result;
}

export default function (api: { registerTool: (tool: unknown, opts?: { optional?: boolean }) => void }) {
  api.registerTool(
    {
      name: "asap_invoke",
      description:
        "Invoke an ASAP Protocol agent by URN. Use this to call agents from the ASAP Lite Registry (e.g. research, coding, summarization). Provide the agent URN, skill ID, and input payload.",
      parameters: Type.Object({
        urn: Type.String({
          description: "ASAP agent URN (e.g. urn:asap:agent:my-agent)",
        }),
        skill: Type.String({
          description: "Skill identifier from the agent manifest (e.g. web_research, summarization)",
        }),
        input: Type.Optional(
          Type.Record(Type.String(), Type.Unknown(), {
            description: "Skill input payload (key-value object)",
          })
        ),
      }),
      async execute(
        _id: string,
        params: { urn: string; skill: string; input?: Record<string, unknown> }
      ) {
        const { urn, skill, input = {} } = params;
        const registryUrl = process.env.ASAP_REGISTRY_URL || DEFAULT_REGISTRY_URL;
        const authToken = process.env.ASAP_AUTH_TOKEN;

        try {
          const agents = await fetchRegistry(registryUrl);
          const entry = findEntryByUrn(agents, urn);
          if (!entry) {
            return {
              content: [
                {
                  type: "text",
                  text: `Error: Agent not found in registry: ${urn}`,
                },
              ],
            };
          }

          const httpEndpoint = getHttpEndpoint(entry);
          const result = await invokeAsapAgent(
            httpEndpoint,
            urn,
            skill,
            input,
            authToken
          );

          const text =
            typeof result === "string"
              ? result
              : JSON.stringify(result, null, 2);
          return {
            content: [{ type: "text", text }],
          };
        } catch (err) {
          if (!(err instanceof Error)) {
            console.warn("[asap-openclaw-skill] Non-Error thrown:", err);
          }
          const message = err instanceof Error ? err.message : String(err);
          return {
            content: [{ type: "text", text: `Error: ${message}` }],
          };
        }
      },
    },
    { optional: true }
  );
}
