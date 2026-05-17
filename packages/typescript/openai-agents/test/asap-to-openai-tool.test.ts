import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as asapClient from "@asap-protocol/client";
import type { CapabilityFetch } from "@asap-protocol/client";
import { capabilityToolKey } from "@asap-protocol/client/adapters/shared";
import { RunContext, invokeFunctionTool } from "@openai/agents";
import { ApprovalRequiredError, CapabilityNotGrantedError } from "../src/errors.js";
import { asapToolsForOpenAIAgents, asapToolsForOpenAIAgentsSync } from "../src/asap-to-openai-tool.js";

const describeCapabilityMock = vi.fn();

vi.mock("@asap-protocol/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@asap-protocol/client")>();
  return {
    ...actual,
    describeCapability: (...args: unknown[]) => describeCapabilityMock(...args),
  };
});

function mockProvider403(code: string, extra: Record<string, unknown> = {}): CapabilityFetch {
  return vi.fn(async () => {
    return new Response(JSON.stringify({ error: { code, ...extra } }), { status: 403 });
  }) as unknown as CapabilityFetch;
}

describe("asapToolsForOpenAIAgents", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  beforeEach(() => {
    vi.restoreAllMocks();
    describeCapabilityMock.mockReset();
    describeCapabilityMock.mockRejectedValue(new Error("describe not configured in this test"));
  });

  it("returns one OpenAI Agents tool per configured capability", async () => {
    describeCapabilityMock.mockResolvedValue({
      name: "demo_echo",
      description: "d",
    });
    const client = {
      provider: new URL("http://localhost:8080/"),
      capabilities: ["urn:asap:cap:demo_echo"],
    };
    const tools = await asapToolsForOpenAIAgents(client);
    expect(tools).toHaveLength(1);
    const tool = tools[0] as { name?: string };
    expect(tool.name).toBe(capabilityToolKey("urn:asap:cap:demo_echo"));
  });

  it("routes tool execution through executeCapability", async () => {
    describeCapabilityMock.mockResolvedValue({
      name: "demo_echo",
      description: "d",
    });
    const spy = vi.spyOn(asapClient, "executeCapability").mockResolvedValue({ ok: true });
    const client = {
      provider: new URL("http://localhost:8080/"),
      capabilities: ["urn:asap:cap:demo_echo"],
      agentJwt: "jwt-test",
    };
    const tools = await asapToolsForOpenAIAgents(client);
    expect(tools).toHaveLength(1);
    await invokeFunctionTool({
      tool: tools[0]!,
      runContext: new RunContext({}),
      input: JSON.stringify({ message: "ping" }),
    });
    expect(spy).toHaveBeenCalledWith(
      client.provider,
      "urn:asap:cap:demo_echo",
      { message: "ping" },
      expect.objectContaining({ agentJwt: "jwt-test" }),
    );
  });

  it("validates LLM arguments with describe-derived JSON Schema → Zod", async () => {
    vi.spyOn(asapClient, "executeCapability").mockResolvedValue({ ok: true });
    describeCapabilityMock.mockResolvedValue({
      name: "demo_echo",
      description: "Echo capability",
      input_schema: {
        type: "object",
        properties: { message: { type: "string" } },
        required: ["message"],
      },
    });
    const client = {
      provider: new URL("http://localhost:8080/"),
      capabilities: ["urn:asap:cap:demo_echo"],
    };
    const tools = await asapToolsForOpenAIAgents(client);
    await expect(
      invokeFunctionTool({
        tool: tools[0]!,
        runContext: new RunContext({}),
        input: JSON.stringify({}),
      }),
    ).rejects.toThrow();

    await invokeFunctionTool({
      tool: tools[0]!,
      runContext: new RunContext({}),
      input: JSON.stringify({ message: "hi" }),
    });
  });

  it("propagates ApprovalRequiredError on approval_required", async () => {
    const fetchMock = mockProvider403("approval_required", {
      message: "human approval pending",
      data: { reason: "policy" },
    });
    describeCapabilityMock.mockResolvedValue({ name: "demo_echo", description: "d" });
    const client = {
      provider: new URL("http://localhost:8080/"),
      capabilities: ["urn:asap:cap:demo_echo"],
      fetch: fetchMock,
    };
    const tools = await asapToolsForOpenAIAgents(client);
    let approvalErr: unknown;
    try {
      await invokeFunctionTool({
        tool: tools[0]!,
        runContext: new RunContext({}),
        input: JSON.stringify({}),
      });
    } catch (e) {
      approvalErr = e;
    }
    expect(approvalErr).toBeInstanceOf(ApprovalRequiredError);
    expect((approvalErr as ApprovalRequiredError).detail).toEqual({ reason: "policy" });
  });

  it("throws CapabilityNotGrantedError with requestCapability hook", async () => {
    const requestCapability = vi.fn();
    const fetchMock = mockProvider403("capability_not_granted", {
      message: "no grant",
      data: { required_capability: "file:read" },
      request_id: "req-1",
    });
    describeCapabilityMock.mockResolvedValue({ name: "file:read", description: "d" });
    const client = {
      provider: new URL("http://localhost:8080/"),
      capabilities: ["file:read"],
      fetch: fetchMock,
    };
    const tools = await asapToolsForOpenAIAgents(client, { requestCapability });
    let err: unknown;
    try {
      await invokeFunctionTool({
        tool: tools[0]!,
        runContext: new RunContext({}),
        input: JSON.stringify({}),
      });
    } catch (e) {
      err = e;
    }
    expect(err).toBeInstanceOf(CapabilityNotGrantedError);
    await (err as CapabilityNotGrantedError).requestCapability();
    expect(requestCapability).toHaveBeenCalledWith("file:read");
  });

  it("denies once then succeeds when provider grants capability", async () => {
    let n = 0;
    const fetchMock = vi.fn(async () => {
      n += 1;
      if (n === 1) {
        return new Response(
          JSON.stringify({
            error: {
              code: "capability_not_granted",
              message: "retry later",
              data: { required_capability: "urn:asap:cap:demo_echo" },
            },
          }),
          { status: 403 },
        );
      }
      return new Response(JSON.stringify({ jsonrpc: "2.0", result: { echoed: "ok" } }), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }) as unknown as CapabilityFetch;

    describeCapabilityMock.mockResolvedValue({ name: "demo_echo", description: "d" });
    const client = {
      provider: new URL("http://localhost:8080/"),
      capabilities: ["urn:asap:cap:demo_echo"],
      fetch: fetchMock,
    };
    const tools = await asapToolsForOpenAIAgents(client);
    await expect(
      invokeFunctionTool({
        tool: tools[0]!,
        runContext: new RunContext({}),
        input: JSON.stringify({ message: "hi" }),
      }),
    ).rejects.toBeInstanceOf(CapabilityNotGrantedError);

    await expect(
      invokeFunctionTool({
        tool: tools[0]!,
        runContext: new RunContext({}),
        input: JSON.stringify({ message: "hi" }),
      }),
    ).resolves.toEqual({ echoed: "ok" });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("does not clone Response for successful executes", async () => {
    describeCapabilityMock.mockResolvedValue({ name: "demo_echo", description: "d" });
    let cloneSpy: ReturnType<typeof vi.spyOn> | undefined;
    const fetchMock = vi.fn(async () => {
      const body = JSON.stringify({ jsonrpc: "2.0", result: { ok: true } });
      const res = new Response(body, {
        status: 200,
        headers: { "content-type": "application/json" },
      });
      cloneSpy = vi.spyOn(res, "clone");
      return res;
    });
    const client = {
      provider: new URL("http://localhost:8080/"),
      capabilities: ["urn:asap:cap:demo_echo"],
      fetch: fetchMock as unknown as CapabilityFetch,
    };
    const tools = await asapToolsForOpenAIAgents(client);
    await invokeFunctionTool({
      tool: tools[0]!,
      runContext: new RunContext({}),
      input: JSON.stringify({ message: "x" }),
    });
    expect(cloneSpy).toBeDefined();
    expect(cloneSpy).not.toHaveBeenCalled();
  });

  it("skips describeCapability when inputSchemas already defines the capability", async () => {
    vi.spyOn(asapClient, "executeCapability").mockResolvedValue({ ok: true });
    describeCapabilityMock.mockResolvedValue({ name: "demo_echo", description: "unused" });
    const client = {
      provider: new URL("http://localhost:8080/"),
      capabilities: ["urn:asap:cap:demo_echo"],
    };
    await asapToolsForOpenAIAgents(client, {
      inputSchemas: {
        "urn:asap:cap:demo_echo": {
          type: "object",
          properties: { message: { type: "string" } },
        },
      },
    });
    expect(describeCapabilityMock).not.toHaveBeenCalled();
  });

  it("builds tools when describeCapability fails", async () => {
    describeCapabilityMock.mockRejectedValue(new Error("describe unavailable"));
    const spy = vi.spyOn(asapClient, "executeCapability").mockResolvedValue({ ok: true });
    const client = {
      provider: new URL("http://localhost:8080/"),
      capabilities: ["urn:asap:cap:demo_echo"],
    };
    const tools = await asapToolsForOpenAIAgents(client);
    expect(tools).toHaveLength(1);
    await invokeFunctionTool({
      tool: tools[0]!,
      runContext: new RunContext({}),
      input: JSON.stringify({}),
    });
    expect(spy).toHaveBeenCalled();
  });

  it("supports asapToolsForOpenAIAgentsSync with inputSchemas", async () => {
    vi.spyOn(asapClient, "executeCapability").mockResolvedValue({ ok: true });
    describeCapabilityMock.mockResolvedValue({ name: "demo_echo", description: "d" });
    const client = {
      provider: new URL("http://localhost:8080/"),
      capabilities: ["urn:asap:cap:demo_echo"],
    };
    const tools = asapToolsForOpenAIAgentsSync(client, {
      inputSchemas: {
        "urn:asap:cap:demo_echo": {
          type: "object",
          properties: { message: { type: "string" } },
          required: ["message"],
        },
      },
    });
    expect(describeCapabilityMock).not.toHaveBeenCalled();
    await expect(
      invokeFunctionTool({
        tool: tools[0]!,
        runContext: new RunContext({}),
        input: JSON.stringify({}),
      }),
    ).rejects.toThrow();
  });
});
