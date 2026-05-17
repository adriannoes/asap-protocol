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

const MAX_BODY_BYTES = 64 * 1024;

const ALLOWED_ORIGINS = new Set(
  [process.env.NEXT_PUBLIC_APP_ORIGIN ?? "http://localhost:3000"].map((s) => s.replace(/\/$/u, "")),
);

function parseProviderAllowlist(): string[] {
  const raw = process.env.ASAP_PROVIDER_ALLOWLIST ?? "127.0.0.1,localhost";
  return raw
    .split(",")
    .map((s) => s.trim().toLowerCase())
    .filter((s) => s.length > 0);
}

const ALLOWED_PROVIDER_HOSTS = parseProviderAllowlist();

type Bucket = { count: number; windowStart: number };

const RATE_BUCKETS = new Map<string, Bucket>();
const RATE_CAPACITY = 60;
const RATE_WINDOW_MS = 60_000;

function rateLimitAllow(key: string): boolean {
  const now = Date.now();
  const existing = RATE_BUCKETS.get(key);
  if (existing === undefined) {
    RATE_BUCKETS.set(key, { count: 1, windowStart: now });
    return true;
  }
  if (now - existing.windowStart >= RATE_WINDOW_MS) {
    existing.count = 0;
    existing.windowStart = now;
  }
  if (existing.count >= RATE_CAPACITY) {
    return false;
  }
  existing.count += 1;
  return true;
}

function clientRateLimitKey(req: Request): string {
  const forwarded = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim();
  if (forwarded !== undefined && forwarded.length > 0) {
    return forwarded;
  }
  const realIp = req.headers.get("x-real-ip")?.trim();
  if (realIp !== undefined && realIp.length > 0) {
    return realIp;
  }
  return "local-direct";
}

function normalizeOrigin(origin: string): string {
  return origin.replace(/\/$/u, "");
}

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

  const originHeader = req.headers.get("origin");
  if (originHeader === null || originHeader === "") {
    return Response.json({ error: "missing_origin" }, { status: 403 });
  }
  if (!ALLOWED_ORIGINS.has(normalizeOrigin(originHeader))) {
    return Response.json({ error: "forbidden_origin" }, { status: 403 });
  }

  const contentLengthHeader = req.headers.get("content-length");
  if (contentLengthHeader !== null && contentLengthHeader.length > 0) {
    const len = Number(contentLengthHeader);
    if (Number.isFinite(len) && len > MAX_BODY_BYTES) {
      return Response.json({ error: "payload_too_large" }, { status: 413 });
    }
  }

  if (!rateLimitAllow(clientRateLimitKey(req))) {
    return Response.json({ error: "rate_limited" }, { status: 429 });
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

  let providerUrlParsed: URL;
  try {
    providerUrlParsed = new URL(providerUrl);
  } catch {
    return Response.json({ error: "invalid_provider_url" }, { status: 400 });
  }
  const host = providerUrlParsed.hostname.toLowerCase();
  if (!ALLOWED_PROVIDER_HOSTS.includes(host)) {
    return Response.json({ error: "provider_not_allowlisted" }, { status: 403 });
  }

  const validation = await safeValidateUIMessages({
    messages,
  });

  if (!validation.success) {
    return Response.json({ error: "Invalid UI messages payload.", details: validation.error.message }, { status: 400 });
  }

  const validated: UIMessage[] = validation.data;

  const client: AsapExecuteClient = {
    provider: providerUrlParsed,
    capabilities,
    agentJwt,
  };

  const agent = await createMastraChatAgent(client);

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
