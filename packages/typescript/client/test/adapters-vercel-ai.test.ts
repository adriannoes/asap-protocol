import { describe, expect, it } from "vitest";
import { generateText, stepCountIs } from "ai";
import { MockLanguageModelV3 } from "ai/test";

import { asapToolsForVercel } from "../src/adapters/vercel-ai.js";
import { capabilityToolKey } from "../src/adapters/shared.js";

describe("adapters / Vercel AI SDK (TS-006)", () => {
  it("exposes at least one tool name derived from the client capabilities", () => {
    const client = {
      provider: new URL("https://example.test/"),
      capabilities: ["urn:asap:cap:echo"],
    };
    const tools = asapToolsForVercel(client);
    expect(Object.keys(tools).length).toBeGreaterThan(0);
    expect(tools.echo).toBeDefined();
  });

  it("generateText with a mock model executes an ASAP tool against the gateway", async () => {
    const capabilityId = "urn:asap:cap:echo";
    const toolKey = capabilityToolKey(capabilityId);

    let capturedBody: string | undefined;
    const fetchFn: typeof fetch = async (_input, init) => {
      capturedBody = typeof init?.body === "string" ? init.body : undefined;
      return new Response(JSON.stringify({ jsonrpc: "2.0", result: { ok: true } }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    };

    const tools = asapToolsForVercel({
      provider: new URL("https://example.test/"),
      capabilities: [capabilityId],
      agentJwt: "test-jwt",
      fetch: fetchFn,
    });

    const model = new MockLanguageModelV3({
      doGenerate: async () => ({
        content: [
          {
            type: "tool-call",
            toolCallId: "call-1",
            toolName: toolKey,
            input: JSON.stringify({ hello: "world" }),
          },
        ],
        finishReason: { unified: "tool-calls", raw: "tool_calls" },
        usage: {
          inputTokens: { total: 1, noCache: 1, cacheRead: undefined, cacheWrite: undefined },
          outputTokens: { total: 1, text: 0, reasoning: undefined },
        },
        warnings: [],
      }),
    });

    await generateText({
      model,
      tools,
      toolChoice: { type: "tool", toolName: toolKey },
      prompt: "invoke the tool",
      stopWhen: stepCountIs(3),
    });

    expect(capturedBody).toBeDefined();
    const parsed = JSON.parse(capturedBody!) as { capability?: string; arguments?: Record<string, unknown> };
    expect(parsed).toMatchObject({
      capability: capabilityId,
      arguments: { hello: "world" },
    });
  });
});
