import { Agent, type AgentConfig } from "@mastra/core/agent";

import type { AsapExecuteClient } from "@asap-protocol/client/adapters/shared";

import { type AsapToolsForMastraOptions, asapToolsForMastra } from "./asap-to-mastra-tool.js";

/** Mastra {@link Agent} model slot — sourced from Mastra's {@link AgentConfig} instead of `ConstructorParameters`. */
export type AsapMastraAgentModel = AgentConfig["model"];

export interface CreateAsapMastraAgentParams {
  readonly client: AsapExecuteClient;
  readonly capabilities: readonly string[];
  /** Mastra model id or config (passed through to {@link Agent}). */
  readonly model: AsapMastraAgentModel;
  /** Optional hooks / schema overrides forwarded to {@link asapToolsForMastra}. */
  readonly toolsOptions?: AsapToolsForMastraOptions;
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
 */
export async function createAsapMastraAgent(params: CreateAsapMastraAgentParams): Promise<Agent> {
  const asapTools = await asapToolsForMastra(
    { ...params.client, capabilities: params.capabilities },
    params.toolsOptions,
  );
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
