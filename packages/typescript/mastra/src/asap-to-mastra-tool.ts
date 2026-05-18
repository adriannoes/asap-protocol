import { describeCapability, executeCapability, type CapabilityFetch } from "@asap-protocol/client";
import {
  capabilityToolKey,
  jsonSchemaForCapabilityInput,
  jsonSchemaForCapabilityOutput,
  type AsapExecuteClient,
} from "@asap-protocol/client/adapters/shared";
import { createTool, type Tool } from "@mastra/core/tools";

import { ApprovalRequiredError, CapabilityNotGrantedError } from "./errors.js";
import { zodFromJsonSchema } from "./json-schema-to-zod.js";

export interface AsapToolsForMastraOptions {
  /**
   * Invoked when the provider returns `403` with `error.code === "capability_not_granted"`.
   * Use this to trigger `request-capability` / host approval flows.
   */
  readonly requestCapability?: (requiredCapability: string) => void | Promise<void>;
  /** Pre-fetched per-capability input schemas (parity with adapters/openai|anthropic). */
  readonly inputSchemas?: Readonly<Record<string, unknown>>;
  /** Pre-fetched per-capability output schemas. */
  readonly outputSchemas?: Readonly<Record<string, unknown>>;
}

function isRecord(x: unknown): x is Record<string, unknown> {
  return typeof x === "object" && x !== null && !Array.isArray(x);
}

/**
 * Wraps a {@link CapabilityFetch} to map select provider HTTP 403 JSON error payloads into typed errors.
 *
 * Unary JSON only: non-403 responses are returned as-is so bodies are not buffered. Do not use this
 * wrapper for SSE or other streaming responses; the contract assumes small JSON payloads suitable for
 * `describeCapability` / `executeCapability`.
 */
function wrapFetchWithCapabilityErrors(
  base: CapabilityFetch | undefined,
  options: AsapToolsForMastraOptions | undefined,
): CapabilityFetch {
  const impl = base ?? globalThis.fetch;
  return async (input, init) => {
    const res = await impl(input, init);
    if (res.status !== 403) {
      return res;
    }
    const text = await res.clone().text();
    let parsed: unknown;
    try {
      parsed = text.length === 0 ? {} : JSON.parse(text);
    } catch {
      return new Response(text, { status: res.status, statusText: res.statusText, headers: res.headers });
    }
    if (!isRecord(parsed)) {
      return new Response(text, { status: res.status, statusText: res.statusText, headers: res.headers });
    }
    if (parsed.error === "constraint_violated") {
      return new Response(text, { status: res.status, statusText: res.statusText, headers: res.headers });
    }
    const errObj = parsed.error;
    if (!isRecord(errObj)) {
      return new Response(text, { status: res.status, statusText: res.statusText, headers: res.headers });
    }
    const code = errObj.code;
    if (code === "capability_not_granted") {
      const data = isRecord(errObj.data) ? errObj.data : undefined;
      const required =
        typeof data?.required_capability === "string" ? data.required_capability : "";
      const msg = typeof errObj.message === "string" ? errObj.message : undefined;
      throw new CapabilityNotGrantedError(required, options?.requestCapability, msg);
    }
    if (code === "approval_required") {
      const msg = typeof errObj.message === "string" ? errObj.message : "Capability execution requires approval";
      throw new ApprovalRequiredError(msg, errObj.data);
    }
    return new Response(text, { status: res.status, statusText: res.statusText, headers: res.headers });
  };
}

function buildTools(
  client: AsapExecuteClient,
  fetchFn: CapabilityFetch,
  describedByCapability: ReadonlyMap<
    string,
    | {
        readonly description: string;
        readonly input_schema?: unknown;
        readonly output_schema?: unknown;
      }
    | undefined
  >,
  options: AsapToolsForMastraOptions | undefined,
): readonly Tool[] {
  const tools: Tool[] = [];
  for (const capabilityId of client.capabilities) {
    const id = capabilityToolKey(capabilityId);
    const described = describedByCapability.get(capabilityId);
    const inputJson = jsonSchemaForCapabilityInput(
      options?.inputSchemas?.[capabilityId] ?? described?.input_schema,
    );
    const outputRaw = options?.outputSchemas?.[capabilityId] ?? described?.output_schema;
    const outputJson = jsonSchemaForCapabilityOutput(outputRaw);

    tools.push(
      createTool({
        id,
        description: described?.description ?? `ASAP capability: ${capabilityId}`,
        inputSchema: zodFromJsonSchema(inputJson),
        outputSchema: zodFromJsonSchema(outputJson),
        execute: async (inputData: unknown) => {
          const ctx =
            typeof inputData === "object" && inputData !== null && !Array.isArray(inputData)
              ? (inputData as Record<string, unknown>)
              : {};
          return executeCapability(client.provider, capabilityId, ctx, {
            agentJwt: client.agentJwt,
            fetch: fetchFn,
          });
        },
      }),
    );
  }
  return tools;
}

/**
 * Build Mastra {@link createTool} instances for each ASAP capability on the client.
 *
 * When {@link AsapToolsForMastraOptions.inputSchemas} does not define a capability entry, this calls
 * {@link describeCapability} once per capability to recover JSON Schemas and descriptions.
 */
export async function asapToolsForMastra(
  client: AsapExecuteClient,
  options?: AsapToolsForMastraOptions,
): Promise<readonly Tool[]> {
  const fetchFn = wrapFetchWithCapabilityErrors(client.fetch, options);
  const describedByCapability = new Map<
    string,
    | {
        readonly description: string;
        readonly input_schema?: unknown;
        readonly output_schema?: unknown;
      }
    | undefined
  >();

  for (const capabilityId of client.capabilities) {
    if (options?.inputSchemas?.[capabilityId] !== undefined) {
      describedByCapability.set(capabilityId, undefined);
      continue;
    }
    const described = await describeCapability(client.provider, capabilityId, {
      fetch: fetchFn,
      agentJwt: client.agentJwt,
    }).catch(() => undefined);

    if (described === undefined) {
      describedByCapability.set(capabilityId, undefined);
    } else {
      describedByCapability.set(capabilityId, {
        description: described.description,
        input_schema: described.input_schema,
        output_schema: described.output_schema,
      });
    }
  }

  return buildTools(client, fetchFn, describedByCapability, options);
}

/**
 * Synchronous variant for callers that already have per-capability {@link AsapToolsForMastraOptions.inputSchemas}
 * / {@link AsapToolsForMastraOptions.outputSchemas} and want to avoid {@link describeCapability} round-trips.
 */
export function asapToolsForMastraSync(
  client: AsapExecuteClient,
  options?: AsapToolsForMastraOptions,
): readonly Tool[] {
  const fetchFn = wrapFetchWithCapabilityErrors(client.fetch, options);
  const describedByCapability = new Map<
    string,
    | {
        readonly description: string;
        readonly input_schema?: unknown;
        readonly output_schema?: unknown;
      }
    | undefined
  >();
  for (const capabilityId of client.capabilities) {
    describedByCapability.set(capabilityId, undefined);
  }
  return buildTools(client, fetchFn, describedByCapability, options);
}
