/** Shared helpers for wiring ASAP capabilities into LLM/agent SDK tool surfaces. */

import type { CapabilityFetch } from "../capabilities.js";

/** Client fields required to execute capabilities over HTTP (Vercel AI adapter). */
export interface AsapExecuteClient {
  readonly provider: URL;
  /** Capability identifiers (URN or short names). */
  readonly capabilities: readonly string[];
  readonly agentJwt?: string;
  readonly fetch?: CapabilityFetch;
}

/** Minimal source for building static tool definitions (OpenAI / Anthropic adapters). */
export interface AsapCapabilityList {
  readonly capabilities: readonly string[];
}

/**
 * Maps a capability id to a stable tool/function name (a-z, A-Z, 0-9, _, -).
 */
export function capabilityToolKey(capabilityId: string): string {
  const stripped = capabilityId.replace(/^urn:asap:cap:/iu, "");
  const sanitized = stripped.replace(/[^a-zA-Z0-9_-]+/gu, "_").replace(/^_+|_+$/gu, "");
  return sanitized.length > 0 ? sanitized : "capability";
}

/**
 * Normalizes describe `input_schema` into a JSON Schema object for provider tool definitions.
 */
export function jsonSchemaForCapabilityInput(inputSchema: unknown | undefined): Record<string, unknown> {
  if (
    typeof inputSchema === "object" &&
    inputSchema !== null &&
    !Array.isArray(inputSchema) &&
    typeof (inputSchema as { type?: unknown }).type === "string"
  ) {
    return inputSchema as Record<string, unknown>;
  }
  return {
    type: "object",
    additionalProperties: true,
    properties: {},
  };
}

/**
 * Normalizes describe `output_schema` into a JSON Schema object for tool output typing.
 *
 * Unlike {@link jsonSchemaForCapabilityInput}, the fallback omits `properties: {}` so consumers
 * that treat "empty object schema" specially still see a conventional open object.
 */
export function jsonSchemaForCapabilityOutput(outputSchema: unknown | undefined): Record<string, unknown> {
  if (
    typeof outputSchema === "object" &&
    outputSchema !== null &&
    !Array.isArray(outputSchema) &&
    typeof (outputSchema as { type?: unknown }).type === "string"
  ) {
    return outputSchema as Record<string, unknown>;
  }
  return { type: "object", additionalProperties: true };
}
