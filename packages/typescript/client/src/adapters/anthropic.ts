/**
 * Anthropic Messages API tool definitions from ASAP capabilities.
 */

import type { AsapCapabilityList } from "./shared.js";
import { capabilityToolKey, jsonSchemaForCapabilityInput } from "./shared.js";

/** Shape aligned with Anthropic Messages `tool` blocks (tool_use). */
export interface AnthropicToolDefinition {
  readonly name: string;
  readonly description: string;
  readonly input_schema: Record<string, unknown>;
}

export interface AsapAnthropicToolsOptions {
  readonly descriptions?: Readonly<Record<string, string>>;
  readonly inputSchemas?: Readonly<Record<string, unknown>>;
}

/**
 * Returns Anthropic-compatible tool definitions for the given capability list.
 */
export function asapToolsForAnthropic(
  source: AsapCapabilityList,
  options?: AsapAnthropicToolsOptions,
): AnthropicToolDefinition[] {
  return source.capabilities.map((capabilityId) => {
    const name = capabilityToolKey(capabilityId);
    const description =
      options?.descriptions?.[capabilityId] ?? `ASAP capability: ${capabilityId}`;
    const input_schema = jsonSchemaForCapabilityInput(options?.inputSchemas?.[capabilityId]);

    return {
      name,
      description,
      input_schema,
    };
  });
}

export type { AsapCapabilityList } from "./shared.js";
