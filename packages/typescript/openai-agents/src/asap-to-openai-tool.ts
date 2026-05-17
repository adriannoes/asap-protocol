import { tool } from "@openai/agents";
import { describeCapability, executeCapability, type CapabilityFetch } from "@asap-protocol/client";
import {
  capabilityToolKey,
  jsonSchemaForCapabilityInput,
  type AsapExecuteClient,
} from "@asap-protocol/client/adapters/shared";
import type { ZodObject } from "zod";
import { z } from "zod";

import { ApprovalRequiredError, CapabilityNotGrantedError } from "./errors.js";
import { zodFromJsonSchema } from "./schema-bridge.js";

/** JSON Schema object accepted by `tool({ strict: false })` (SDK types are not exported from `@openai/agents`). */
type OpenAIAgentsNonStrictToolParameters = Extract<Parameters<typeof tool>[0], { strict: false }>["parameters"];

type BuiltToolParameters =
  | { readonly mode: "zod"; readonly schema: ZodObject<Record<string, z.ZodTypeAny>> }
  | { readonly mode: "json"; readonly schema: Record<string, unknown> };

function buildToolParameters(inputJson: Record<string, unknown>): BuiltToolParameters {
  const props = inputJson.properties;
  const hasProps =
    inputJson.type === "object" &&
    typeof props === "object" &&
    props !== null &&
    !Array.isArray(props) &&
    Object.keys(props).length > 0;

  if (hasProps) {
    const zSch = zodFromJsonSchema(inputJson);
    if (zSch instanceof z.ZodObject) {
      return { mode: "zod", schema: zSch.strict() };
    }
  }

  return { mode: "json", schema: inputJson };
}

export interface AsapToolsForOpenAIAgentsOptions {
  /**
   * Invoked when the provider returns `403` with `error.code === "capability_not_granted"`.
   */
  readonly requestCapability?: (requiredCapability: string) => void | Promise<void>;
  readonly inputSchemas?: Readonly<Record<string, unknown>>;
  readonly outputSchemas?: Readonly<Record<string, unknown>>;
}

function isRecord(x: unknown): x is Record<string, unknown> {
  return typeof x === "object" && x !== null && !Array.isArray(x);
}

function wrapFetchWithCapabilityErrors(
  base: CapabilityFetch | undefined,
  options: AsapToolsForOpenAIAgentsOptions | undefined,
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
      const msg =
        typeof errObj.message === "string" ? errObj.message : "Capability execution requires approval";
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
  options: AsapToolsForOpenAIAgentsOptions | undefined,
): ReturnType<typeof tool>[] {
  const tools: ReturnType<typeof tool>[] = [];
  for (const capabilityId of client.capabilities) {
    const id = capabilityToolKey(capabilityId);
    const described = describedByCapability.get(capabilityId);
    const inputJson = jsonSchemaForCapabilityInput(
      options?.inputSchemas?.[capabilityId] ?? described?.input_schema,
    );

    const built = buildToolParameters(inputJson);

    const exec = async (input: unknown): Promise<unknown> => {
      const ctx = isRecord(input) ? input : {};
      return executeCapability(client.provider, capabilityId, ctx, {
        agentJwt: client.agentJwt,
        fetch: fetchFn,
      });
    };

    if (built.mode === "zod") {
      tools.push(
        tool({
          name: id,
          description: described?.description ?? `ASAP capability: ${capabilityId}`,
          parameters: built.schema,
          strict: true,
          errorFunction: null,
          execute: exec,
        }),
      );
    } else {
      tools.push(
        tool({
          name: id,
          description: described?.description ?? `ASAP capability: ${capabilityId}`,
          parameters: built.schema as OpenAIAgentsNonStrictToolParameters,
          strict: false,
          errorFunction: null,
          execute: exec,
        }),
      );
    }
  }
  return tools;
}

/**
 * Build OpenAI Agents SDK {@link tool} instances for each ASAP capability on the client.
 *
 * Uses top-level {@link executeCapability} from `@asap-protocol/client` on each execution path.
 */
export async function asapToolsForOpenAIAgents(
  client: AsapExecuteClient,
  options?: AsapToolsForOpenAIAgentsOptions,
): Promise<readonly ReturnType<typeof tool>[]> {
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
 * Synchronous variant when {@link AsapToolsForOpenAIAgentsOptions.inputSchemas} / `outputSchemas`
 * are already materialized (skips describe round-trips).
 */
export function asapToolsForOpenAIAgentsSync(
  client: AsapExecuteClient,
  options?: AsapToolsForOpenAIAgentsOptions,
): readonly ReturnType<typeof tool>[] {
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
