import { openai } from "@ai-sdk/openai";
import type { AsapExecuteClient } from "@asap-protocol/client/adapters/shared";
import { createAsapMastraAgent } from "@asap-protocol/mastra";

/**
 * Build a Mastra {@link Agent} with ASAP capability tools routed through the gateway.
 *
 * Keeps Mastra/OpenAI wiring in one place per the sprint scaffold (`src/mastra/`).
 * Return type is inferred from {@link createAsapMastraAgent} so this module does not import
 * `Agent` from a second resolved copy of `@mastra/core` in the pnpm graph.
 */
export async function createMastraChatAgent(
  client: AsapExecuteClient,
  modelId = "gpt-4o-mini",
): Promise<Awaited<ReturnType<typeof createAsapMastraAgent>>> {
  return createAsapMastraAgent({
    client,
    capabilities: [...client.capabilities],
    model: openai(modelId),
  });
}
