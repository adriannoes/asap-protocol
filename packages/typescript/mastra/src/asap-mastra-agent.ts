import { Agent } from "@mastra/core/agent";

import type { AsapExecuteClient } from "@asap-protocol/client/adapters/shared";

import { asapToolsForMastra } from "./asap-to-mastra-tool.js";

export interface CreateAsapMastraAgentParams {
  readonly client: AsapExecuteClient;
  readonly capabilities: readonly string[];
  /** Mastra model id or config (passed through to {@link Agent}). */
  readonly model: ConstructorParameters<typeof Agent>[0]["model"];
  /** Overrides {@link Agent} id (default: `asap-mastra-agent`). */
  readonly agentId?: string;
  /** Overrides display name (default: `ASAP Mastra Agent`). */
  readonly name?: string;
  /**
   * Overrides default system instructions. When omitted, instructions list the capability URNs
   * and tell the model to call tools with valid JSON arguments.
   */
  readonly instructions?: string;
}

function defaultInstructions(capabilities: readonly string[]): string {
  const list = capabilities.length > 0 ? capabilities.join(", ") : "(none configured)";
  return [
    "You have access to ASAP capabilities exposed as Mastra tools.",
    "When the user asks to run a capability on the ASAP provider, call the matching tool with valid JSON arguments derived from the capability schema.",
    `Capability URNs available on this agent: ${list}.`,
    "Answer concisely in natural language after tools return.",
  ].join(" ");
}

/**
 * Convenience wrapper that mounts ASAP-derived tools on a Mastra {@link Agent}.
 *
 * @see sprint task 3.1 for wiring {@link asapToolsForMastra}.
 */
export function createAsapMastraAgent(params: CreateAsapMastraAgentParams): Agent {
  const clientForTools: AsapExecuteClient = {
    ...params.client,
    capabilities: params.capabilities,
  };
  const asapTools = asapToolsForMastra(clientForTools);
  const tools: Record<string, (typeof asapTools)[number]> = {};
  for (const t of asapTools) {
    tools[t.id] = t;
  }
  return new Agent({
    id: params.agentId ?? "asap-mastra-agent",
    name: params.name ?? "ASAP Mastra Agent",
    instructions: params.instructions ?? defaultInstructions(params.capabilities),
    model: params.model,
    tools,
  });
}
