import { executeCapability, type CapabilityFetch } from "@asap-protocol/client";
import {
  capabilityToolKey,
  jsonSchemaForCapabilityInput,
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
}

function isRecord(x: unknown): x is Record<string, unknown> {
  return typeof x === "object" && x !== null && !Array.isArray(x);
}

function wrapFetchWithCapabilityErrors(
  base: CapabilityFetch | undefined,
  options: AsapToolsForMastraOptions | undefined,
): CapabilityFetch {
  const impl = base ?? globalThis.fetch;
  return async (input, init) => {
    const res = await impl(input, init);
    const text = await res.text();
    if (res.status !== 403) {
      return new Response(text, { status: res.status, statusText: res.statusText, headers: res.headers });
    }
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

/**
 * Build Mastra {@link createTool} instances for each ASAP capability on the client.
 */
export function asapToolsForMastra(
  client: AsapExecuteClient,
  options?: AsapToolsForMastraOptions,
): readonly Tool[] {
  const fetchFn = wrapFetchWithCapabilityErrors(client.fetch, options);
  const tools: Tool[] = [];

  for (const capabilityId of client.capabilities) {
    const id = capabilityToolKey(capabilityId);
    const inputJson = jsonSchemaForCapabilityInput(undefined);
    const outputJson = jsonSchemaForCapabilityInput(undefined);

    tools.push(
      createTool({
        id,
        description: `ASAP capability: ${capabilityId}`,
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
