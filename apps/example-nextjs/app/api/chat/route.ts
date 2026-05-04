import { openai } from "@ai-sdk/openai";
import { asapToolsForVercel } from "@asap-protocol/client/adapters/vercel-ai";
import { convertToModelMessages, stepCountIs, streamText, type UIMessage } from "ai";
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
  const provider = new URL(providerUrl);

  const tools = asapToolsForVercel({
    provider,
    capabilities,
    agentJwt,
  });

  const uiMessages = messages as UIMessage[];

  const result = streamText({
    model: openai("gpt-4o-mini"),
    system:
      "You are a concise assistant. Use ASAP tools when the user wants to run a registered capability on the gateway.",
    messages: await convertToModelMessages(uiMessages),
    tools,
    stopWhen: stepCountIs(12),
  });

  return result.toUIMessageStreamResponse();
}
