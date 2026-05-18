import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as asapClient from "@asap-protocol/client";
import type { CapabilityFetch } from "@asap-protocol/client";
import { capabilityToolKey } from "@asap-protocol/client/adapters/shared";
import { ApprovalRequiredError, CapabilityNotGrantedError } from "../src/errors.js";
import { asapToolsForMastra, asapToolsForMastraSync } from "../src/asap-to-mastra-tool.js";

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

describe("asapToolsForMastra", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  beforeEach(() => {
    vi.restoreAllMocks();
    describeCapabilityMock.mockReset();
    describeCapabilityMock.mockRejectedValue(new Error("describe not configured in this test"));
  });

  it("returns one Mastra tool per configured capability", async () => {
    describeCapabilityMock.mockResolvedValue({
      name: "demo_echo",
      description: "d",
    });
    const client = {
      provider: new URL("http://localhost:8080/"),
      capabilities: ["urn:asap:cap:demo_echo"],
    };
    const tools = await asapToolsForMastra(client);
    expect(tools).toHaveLength(1);
    const tool = tools[0] as { id: string };
    expect(tool.id).toBe(capabilityToolKey("urn:asap:cap:demo_echo"));
  });

  it("routes tool execution to executeCapability with provider, name, args, and options", async () => {
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
    const tools = await asapToolsForMastra(client);
    expect(tools).toHaveLength(1);
    const tool = tools[0] as { execute?: (input: unknown, ctx?: unknown) => Promise<unknown> };
    await tool.execute?.({ message: "ping" });
    expect(spy).toHaveBeenCalledWith(
      client.provider,
      "urn:asap:cap:demo_echo",
      { message: "ping" },
      expect.objectContaining({ agentJwt: "jwt-test" }),
    );
  });

  it("normalizes non-object tool input to an empty execution payload", async () => {
    describeCapabilityMock.mockResolvedValue({
      name: "demo_echo",
      description: "d",
    });
    const spy = vi.spyOn(asapClient, "executeCapability").mockResolvedValue({ ok: true });
    const client = {
      provider: new URL("http://localhost:8080/"),
      capabilities: ["urn:asap:cap:demo_echo"],
    };
    const tools = await asapToolsForMastra(client);
    const tool = tools[0] as { execute?: (input: unknown) => Promise<unknown> };
    await tool.execute?.("not an object");
    expect(spy).toHaveBeenCalledWith(
      client.provider,
      "urn:asap:cap:demo_echo",
      {},
      expect.any(Object),
    );
  });

  it("derives strict input schemas from describeCapability when inputSchemas are not pre-supplied", async () => {
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
    const tools = await asapToolsForMastra(client);
    const tool = tools[0] as { inputSchema?: { safeParse: (v: unknown) => { success: boolean } } };
    expect(tool.inputSchema?.safeParse({}).success).toBe(false);
  });

  it("keeps building tools with fallback descriptions when capability discovery fails", async () => {
    describeCapabilityMock.mockRejectedValue(new Error("provider unavailable"));
    const client = {
      provider: new URL("http://localhost:8080/"),
      capabilities: ["urn:asap:cap:demo_echo"],
    };
    const tools = await asapToolsForMastra(client);
    const tool = tools[0] as { description?: string };
    expect(tool.description).toBe("ASAP capability: urn:asap:cap:demo_echo");
  });

  it("skips async capability discovery for pre-supplied input schemas only", async () => {
    describeCapabilityMock.mockImplementation(async (_provider: URL, capability: string) => ({
      name: capability,
      description: "discovered",
    }));
    const client = {
      provider: new URL("http://localhost:8080/"),
      capabilities: ["urn:asap:cap:cached", "urn:asap:cap:discovered"],
    };
    const tools = await asapToolsForMastra(client, {
      inputSchemas: {
        "urn:asap:cap:cached": {
          type: "object",
          properties: { message: { type: "string" } },
          required: ["message"],
        },
      },
    });
    expect(tools).toHaveLength(2);
    expect(describeCapabilityMock).toHaveBeenCalledTimes(1);
    expect(describeCapabilityMock).toHaveBeenCalledWith(
      client.provider,
      "urn:asap:cap:discovered",
      expect.any(Object),
    );
  });

  it("applies pre-supplied output schemas to generated tools", async () => {
    describeCapabilityMock.mockResolvedValue({
      name: "demo_echo",
      description: "d",
    });
    const client = {
      provider: new URL("http://localhost:8080/"),
      capabilities: ["urn:asap:cap:demo_echo"],
    };
    const tools = await asapToolsForMastra(client, {
      outputSchemas: {
        "urn:asap:cap:demo_echo": {
          type: "object",
          properties: { answer: { type: "string" } },
          required: ["answer"],
        },
      },
    });
    const tool = tools[0] as { outputSchema?: { safeParse: (v: unknown) => { success: boolean } } };
    expect(tool.outputSchema?.safeParse({ answer: "pong" }).success).toBe(true);
    expect(tool.outputSchema?.safeParse({}).success).toBe(false);
  });

  it("throws ApprovalRequiredError when the provider returns approval_required (403)", async () => {
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
    const tools = await asapToolsForMastra(client);
    const tool = tools[0] as { execute?: (input: unknown) => Promise<unknown> };
    let approvalErr: unknown;
    try {
      await tool.execute?.({});
    } catch (e) {
      approvalErr = e;
    }
    expect(approvalErr).toBeInstanceOf(ApprovalRequiredError);
    expect((approvalErr as ApprovalRequiredError).detail).toEqual({ reason: "policy" });
  });

  it("throws CapabilityNotGrantedError and exposes requestCapability hook on capability_not_granted", async () => {
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
    const tools = await asapToolsForMastra(client, { requestCapability });
    const tool = tools[0] as { execute?: (input: unknown) => Promise<unknown> };
    let err: unknown;
    try {
      await tool.execute?.({});
    } catch (e) {
      err = e;
    }
    expect(err).toBeInstanceOf(CapabilityNotGrantedError);
    await (err as CapabilityNotGrantedError).requestCapability();
    expect(requestCapability).toHaveBeenCalledWith("file:read");
  });

  it("preserves an empty required capability when capability_not_granted omits data", async () => {
    const requestCapability = vi.fn();
    const fetchMock = mockProvider403("capability_not_granted", {
      message: "no grant metadata",
    });
    describeCapabilityMock.mockResolvedValue({ name: "file:read", description: "d" });
    const client = {
      provider: new URL("http://localhost:8080/"),
      capabilities: ["file:read"],
      fetch: fetchMock,
    };
    const tools = await asapToolsForMastra(client, { requestCapability });
    const tool = tools[0] as { execute?: (input: unknown) => Promise<unknown> };
    let err: unknown;
    try {
      await tool.execute?.({});
    } catch (e) {
      err = e;
    }
    expect(err).toBeInstanceOf(CapabilityNotGrantedError);
    expect((err as CapabilityNotGrantedError).requiredCapability).toBe("");
    await (err as CapabilityNotGrantedError).requestCapability();
    expect(requestCapability).toHaveBeenCalledWith("");
  });

  it("does not call Response.clone for non-403 execute responses", async () => {
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
      fetch: fetchMock,
    };
    const tools = await asapToolsForMastra(client);
    const tool = tools[0] as { execute?: (input: unknown) => Promise<unknown> };
    await tool.execute?.({ message: "x" });
    expect(cloneSpy).toBeDefined();
    expect(cloneSpy).not.toHaveBeenCalled();
  });

  it("returns constraint_violated 403 responses for executeCapability to parse", async () => {
    const fetchMock = vi.fn(async () => {
      return new Response(
        JSON.stringify({
          error: "constraint_violated",
          capability: "urn:asap:cap:demo_echo",
          violations: [{ field: "message", operator: "required", message: "required" }],
        }),
        { status: 403, headers: { "content-type": "application/json" } },
      );
    });
    describeCapabilityMock.mockResolvedValue({ name: "demo_echo", description: "d" });
    const client = {
      provider: new URL("http://localhost:8080/"),
      capabilities: ["urn:asap:cap:demo_echo"],
      fetch: fetchMock,
    };
    const tools = await asapToolsForMastra(client);
    const tool = tools[0] as { execute?: (input: unknown) => Promise<unknown> };
    await expect(tool.execute?.({})).rejects.toThrow(/constraint violated/i);
  });

  it("skips describeCapability when inputSchemas already defines the capability", async () => {
    vi.spyOn(asapClient, "executeCapability").mockResolvedValue({ ok: true });
    describeCapabilityMock.mockResolvedValue({ name: "demo_echo", description: "unused" });
    const client = {
      provider: new URL("http://localhost:8080/"),
      capabilities: ["urn:asap:cap:demo_echo"],
    };
    await asapToolsForMastra(client, {
      inputSchemas: {
        "urn:asap:cap:demo_echo": {
          type: "object",
          properties: { message: { type: "string" } },
        },
      },
      outputSchemas: {
        "urn:asap:cap:demo_echo": { type: "object", additionalProperties: true },
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
    const tools = await asapToolsForMastra(client);
    expect(tools).toHaveLength(1);
    const tool = tools[0] as { execute?: (input: unknown) => Promise<unknown> };
    await tool.execute?.({});
    expect(spy).toHaveBeenCalled();
  });

  it("exposes asapToolsForMastraSync for pre-supplied schemas", () => {
    const client = {
      provider: new URL("http://localhost:8080/"),
      capabilities: ["urn:asap:cap:demo_echo"],
    };
    const tools = asapToolsForMastraSync(client, {
      inputSchemas: {
        "urn:asap:cap:demo_echo": {
          type: "object",
          properties: { message: { type: "string" } },
          required: ["message"],
        },
      },
    });
    expect(describeCapabilityMock).not.toHaveBeenCalled();
    const tool = tools[0] as { inputSchema?: { safeParse: (v: unknown) => { success: boolean } } };
    expect(tool.inputSchema?.safeParse({}).success).toBe(false);
  });
});
