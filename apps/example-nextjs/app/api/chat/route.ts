import { openai } from "@ai-sdk/openai";
import { asapToolsForVercel } from "@asap-protocol/client/adapters/vercel-ai";
import { convertToModelMessages, stepCountIs, streamText } from "ai";

export const maxDuration = 60;

export async function POST(req: Request) {
  if (!process.env.OPENAI_API_KEY?.trim()) {
    return Response.json({ error: "Set OPENAI_API_KEY to enable the chat route." }, { status: 503 });
  }

  const body = (await req.json()) as Record<string, unknown>;
  const messages = body.messages;
  const providerUrl = typeof body.providerUrl === "string" ? body.providerUrl : "";
  const agentJwt = typeof body.agentJwt === "string" ? body.agentJwt : undefined;

  let capabilities: string[] = [];
  if (Array.isArray(body.capabilities)) {
    capabilities = body.capabilities.filter((x): x is string => typeof x === "string");
  }

  if (!providerUrl || capabilities.length === 0) {
    return Response.json({ error: "providerUrl and capabilities are required." }, { status: 400 });
  }

  let provider: URL;
  try {
    provider = new URL(providerUrl);
  } catch {
    return Response.json({ error: "Invalid providerUrl." }, { status: 400 });
  }

  const tools = asapToolsForVercel({
    provider,
    capabilities,
    agentJwt,
  });

  const uiMessages = Array.isArray(messages) ? messages : [];

  const result = streamText({
    model: openai("gpt-4o-mini"),
    system:
      "You are a concise assistant. Use ASAP tools when the user wants to run a registered capability on the gateway.",
    messages: await convertToModelMessages(uiMessages as never),
    tools,
    stopWhen: stepCountIs(12),
  });

  return result.toUIMessageStreamResponse();
}
