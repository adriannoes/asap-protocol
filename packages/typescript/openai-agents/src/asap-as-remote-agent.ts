import { Agent, type AgentInputItem } from "@openai/agents";

import type { AsapExecuteClient } from "@asap-protocol/client/adapters/shared";

import {
  type AsapToolsForOpenAIAgentsOptions,
  asapToolsForOpenAIAgents,
} from "./asap-to-openai-tool.js";

export type AsapRemoteAgentMode = "delegated" | "autonomous";

/** Mutable bag carried through {@link RunContext} when using {@link asapAsRemoteAgent}. */
export interface AsapRemoteRunContext {
  /** Latest draft ASAP envelope captured when this agent starts (including after an SDK handoff). */
  lastAsapHandoffEnvelope?: Record<string, unknown>;
}

export interface AsapAsRemoteAgentOptions {
  readonly mode?: AsapRemoteAgentMode;
  readonly name?: string;
  readonly instructions?: string | undefined;
  readonly handoffDescription?: string;
  readonly model?: string;
  readonly toolsOptions?: AsapToolsForOpenAIAgentsOptions;
}

function serializeTurnInput(turnInput: string | AgentInputItem[] | undefined): string {
  if (turnInput === undefined) {
    return "";
  }
  if (typeof turnInput === "string") {
    return turnInput;
  }
  try {
    return JSON.stringify(turnInput);
  } catch {
    return "";
  }
}

/**
 * Draft `task.request`-style envelope metadata used when delegating from OpenAI Agents handoffs to ASAP.
 *
 * The gateway still performs authorization and routing; this object mirrors how adapters attach agent mode.
 */
export function draftTaskRequestEnvelopeForRemoteAgent(params: {
  readonly mode: AsapRemoteAgentMode;
  readonly providerUrl: URL;
  readonly turnInput?: string | AgentInputItem[];
}): Record<string, unknown> {
  const delegatedInput = serializeTurnInput(params.turnInput);
  return {
    asap_version: "2.2",
    sender: "urn:asap:agent:openai-agents-adapter",
    recipient: params.providerUrl.href,
    payload_type: "task.request",
    payload: {
      conversation_id: "openai-agents-handoff",
      skill_id: "asap-remote-handoff",
      input: {
        query: delegatedInput,
        asap_agent_mode: params.mode,
      },
    },
    extensions: {
      asap_agent_mode: params.mode,
    },
  };
}

function defaultInstructions(mode: AsapRemoteAgentMode, capabilities: readonly string[]): string {
  const list = capabilities.length > 0 ? capabilities.join(", ") : "(none configured)";
  return [
    "You are an ASAP-backed specialist agent invoked via OpenAI Agents SDK handoffs.",
    `Operate in ${mode} mode with respect to host policy.`,
    `Use the ASAP capability tools wired for this agent (deterministic keys). Capability URNs: ${list}.`,
    "Pass structured JSON arguments that satisfy each capability schema.",
  ].join(" ");
}

function resolveProvider(providerUrl: string | URL): URL {
  return typeof providerUrl === "string" ? new URL(providerUrl) : providerUrl;
}

/**
 * Returns an OpenAI Agents {@link Agent} backed by ASAP capability tools on `providerUrl`.
 *
 * Subscribes to `agent_start` so {@link AsapRemoteRunContext.lastAsapHandoffEnvelope} captures draft envelope metadata
 * (including {@link AsapAsRemoteAgentOptions.mode}) whenever this agent begins a turn—including after an SDK handoff.
 */
export async function asapAsRemoteAgent(
  client: AsapExecuteClient,
  providerUrl: string | URL,
  options?: AsapAsRemoteAgentOptions,
): Promise<Agent<AsapRemoteRunContext>> {
  const mode = options?.mode ?? "delegated";
  const resolvedProvider = resolveProvider(providerUrl);
  const mergedClient: AsapExecuteClient = {
    ...client,
    provider: resolvedProvider,
  };

  const tools = await asapToolsForOpenAIAgents(mergedClient, options?.toolsOptions);

  const agent = new Agent<AsapRemoteRunContext>({
    name: options?.name ?? `asap-remote-${resolvedProvider.hostname}`,
    instructions: options?.instructions ?? defaultInstructions(mode, mergedClient.capabilities),
    handoffDescription:
      options?.handoffDescription ??
      `Delegates to ASAP capabilities at ${resolvedProvider.href} (${mode} mode).`,
    model: options?.model ?? "gpt-4o-mini",
    tools: [...tools],
  });

  agent.on("agent_start", (runContext, _self, turnInput) => {
    runContext.context.lastAsapHandoffEnvelope = draftTaskRequestEnvelopeForRemoteAgent({
      mode,
      providerUrl: resolvedProvider,
      turnInput,
    });
  });

  return agent;
}
