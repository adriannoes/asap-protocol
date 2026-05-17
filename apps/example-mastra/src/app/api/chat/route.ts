import { createMastraChatAgent } from "@/mastra";
import type { AsapExecuteClient } from "@asap-protocol/client/adapters/shared";
import type { MessageListInput } from "@mastra/core/agent/message-list";
import {
  convertToModelMessages,
  createUIMessageStream,
  createUIMessageStreamResponse,
  generateId,
  safeValidateUIMessages,
  type UIMessage,
} from "ai";
import { z } from "zod";

export const maxDuration = 60;

const chatBodySchema = z
  .object({
    messages: z.array(z.unknown()),
    providerUrl: z.string().url(),
    capabilities: z.array(z.string()).min(1),
    agentJwt: z.string().optional(),
  })
  .passthrough();

export async function POST(req: Request) {
  if (!process.env.OPENAI_API_KEY?.trim()) {
    return Response.json({ error: "Set OPENAI_API_KEY to enable the chat route." }, { status: 503 });
  }

  let json: unknown;
  try {
    json = await req.json();
  } catch {
    return Response.json({ error: "Invalid JSON body." }, { status: 400 });
  }

  const parsed = chatBodySchema.safeParse(json);
  if (!parsed.success) {
    return Response.json({ error: parsed.error.flatten() }, { status: 400 });
  }

  const { messages, providerUrl, capabilities, agentJwt } = parsed.data;

  const validation = await safeValidateUIMessages({
    messages,
  });

  if (!validation.success) {
    return Response.json({ error: "Invalid UI messages payload.", details: validation.error.message }, { status: 400 });
  }

  const validated: UIMessage[] = validation.data;

  const client: AsapExecuteClient = {
    provider: new URL(providerUrl),
    capabilities,
    agentJwt,
  };

  const agent = createMastraChatAgent(client);

  const stream = createUIMessageStream<UIMessage>({
    originalMessages: validated,
    execute: async ({ writer }) => {
      const textId = generateId();
      writer.write({ type: "text-start", id: textId });
      try {
        const modelMessages = await convertToModelMessages(
          validated.map((message) => {
            const { id, ...rest } = message;
            void id;
            return rest;
          }),
        );
        // Mastra's `MessageListInput` uses nominal AI SDK v6 types; `ModelMessage[]` from `ai` is runtime-compatible.
        const output = await agent.stream(modelMessages as MessageListInput, { maxSteps: 12 });
        const reader = output.textStream.getReader();
        try {
          let readDone = false;
          while (!readDone) {
            const chunk = await reader.read();
            readDone = chunk.done;
            if (readDone !== true && typeof chunk.value === "string" && chunk.value.length > 0) {
              writer.write({ type: "text-delta", id: textId, delta: chunk.value });
            }
          }
        } finally {
          reader.releaseLock();
        }
      } catch (err) {
        writer.write({
          type: "error",
          errorText: err instanceof Error ? err.message : String(err),
        });
      }
      writer.write({ type: "text-end", id: textId });
    },
  });

  return createUIMessageStreamResponse({ stream });
}
