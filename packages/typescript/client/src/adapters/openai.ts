/**
 * OpenAI Chat Completions `tools` array from ASAP capabilities (TS-007).
 */

import type { AsapCapabilityList } from "./shared.js";
import { capabilityToolKey, jsonSchemaForCapabilityInput } from "./shared.js";

/** Shape aligned with OpenAI `ChatCompletionTool` (function tools). */
export interface OpenAiChatCompletionTool {
  readonly type: "function";
  readonly function: {
    readonly name: string;
    readonly description: string;
    readonly parameters: Record<string, unknown>;
  };
}

export interface AsapOpenAiToolsOptions {
  /** Per-capability description overrides (keyed by full capability id). */
  readonly descriptions?: Readonly<Record<string, string>>;
  /** Per-capability JSON Schema overrides for `function.parameters` (keyed by full capability id). */
  readonly inputSchemas?: Readonly<Record<string, unknown>>;
}

/**
 * Returns OpenAI-compatible tool definitions for the given capability list.
 */
export function asapToolsForOpenAI(
  source: AsapCapabilityList,
  options?: AsapOpenAiToolsOptions,
): OpenAiChatCompletionTool[] {
  return source.capabilities.map((capabilityId) => {
    const name = capabilityToolKey(capabilityId);
    const description =
      options?.descriptions?.[capabilityId] ?? `ASAP capability: ${capabilityId}`;
    const parameters = jsonSchemaForCapabilityInput(options?.inputSchemas?.[capabilityId]);

    return {
      type: "function",
      function: {
        name,
        description,
        parameters,
      },
    };
  });
}

export type { AsapCapabilityList } from "./shared.js";
