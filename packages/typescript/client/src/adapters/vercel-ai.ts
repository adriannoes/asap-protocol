/**
 * Maps an ASAP client to Vercel AI SDK `tools` for `streamText` / `generateText` (TS-006).
 */

import { tool, zodSchema, type Tool } from "ai";
import { z } from "zod";

import { executeCapability } from "../capabilities.js";
import type { AsapExecuteClient } from "./shared.js";
import { capabilityToolKey } from "./shared.js";

/**
 * Builds a `tools` record for the Vercel AI SDK from ASAP capabilities.
 * Each tool executes {@link executeCapability} against `client.provider`.
 */
export function asapToolsForVercel(
  client: AsapExecuteClient,
): Record<string, Tool<Record<string, unknown>, unknown>> {
  const capabilityArgsSchema = zodSchema(
    z.record(z.string(), z.unknown()).describe(
      "Arguments forwarded to POST /asap/capability/execute as the capability `arguments` object.",
    ),
  );
  const fetchFn = client.fetch;
  const tools: Record<string, Tool<Record<string, unknown>, unknown>> = {};

  for (const capabilityId of client.capabilities) {
    const key = capabilityToolKey(capabilityId);
    const cap = capabilityId;
    tools[key] = tool<Record<string, unknown>, unknown>({
      description: `ASAP capability: ${cap}`,
      inputSchema: capabilityArgsSchema,
      execute: async (args: Record<string, unknown>) => {
        return executeCapability(client.provider, cap, args, {
          agentJwt: client.agentJwt,
          fetch: fetchFn,
        });
      },
    });
  }

  return tools;
}

export type { AsapExecuteClient } from "./shared.js";
