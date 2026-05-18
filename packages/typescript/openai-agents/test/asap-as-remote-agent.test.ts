import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as asapClient from "@asap-protocol/client";
import { capabilityToolKey } from "@asap-protocol/client/adapters/shared";
import { RunContext, invokeFunctionTool, type AgentInputItem, type FunctionTool } from "@openai/agents";
import {
  asapAsRemoteAgent,
  draftTaskRequestEnvelopeForRemoteAgent,
  sameProviderOrigin,
  type AsapRemoteRunContext,
} from "../src/asap-as-remote-agent.js";

const describeCapabilityMock = vi.fn();

vi.mock("@asap-protocol/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@asap-protocol/client")>();
  return {
    ...actual,
    describeCapability: (...args: unknown[]) => describeCapabilityMock(...args),
  };
});

describe("draftTaskRequestEnvelopeForRemoteAgent", () => {
  it("includes asap_agent_mode for delegated", () => {
    const draft = draftTaskRequestEnvelopeForRemoteAgent({
      mode: "delegated",
      providerUrl: new URL("http://localhost:8080/"),
      turnInput: "hello",
    });
    expect(draft.extensions).toEqual({ asap_agent_mode: "delegated" });
    expect((draft.payload as Record<string, unknown>).input).toMatchObject({
      asap_agent_mode: "delegated",
      query: "hello",
    });
  });

  it("records autonomous mode separately", () => {
    const draft = draftTaskRequestEnvelopeForRemoteAgent({
      mode: "autonomous",
      providerUrl: new URL("https://gw.example/"),
    });
    expect(draft.extensions).toEqual({ asap_agent_mode: "autonomous" });
  });

  it("uses empty query when turn input cannot be JSON-serialized", () => {
    const circular: unknown[] = [];
    circular.push(circular);
    const draft = draftTaskRequestEnvelopeForRemoteAgent({
      mode: "delegated",
      providerUrl: new URL("http://localhost:8080/"),
      turnInput: circular as AgentInputItem[],
    });
    expect((draft.payload as { input?: { query?: string } }).input?.query).toBe("");
  });
});

describe("sameProviderOrigin", () => {
  it("matches origin and pathname", () => {
    expect(sameProviderOrigin(new URL("https://a.example/"), new URL("https://a.example/"))).toBe(true);
    expect(sameProviderOrigin(new URL("https://a.example/"), new URL("https://b.example/"))).toBe(false);
    expect(
      sameProviderOrigin(new URL("https://a.example/v1/"), new URL("https://a.example/v2/")),
    ).toBe(false);
  });
});

describe("asapAsRemoteAgent", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  beforeEach(() => {
    vi.restoreAllMocks();
    describeCapabilityMock.mockReset();
    describeCapabilityMock.mockRejectedValue(new Error("describe not configured in this test"));
  });

  it("rejects client.agentJwt when providerUrl differs before any fetch", async () => {
    const fetchMock = vi.fn();
    const client = {
      provider: new URL("https://a.example/"),
      capabilities: [],
      agentJwt: "token",
      fetch: fetchMock,
    };

    await expect(asapAsRemoteAgent(client, "https://b.example/")).rejects.toThrow(/remoteAgentJwt/);
    expect(fetchMock).not.toHaveBeenCalled();
    expect(describeCapabilityMock).not.toHaveBeenCalled();
  });

  it("POSTs task.request via asap.send on agent_start", async () => {
    describeCapabilityMock.mockResolvedValue({
      name: "demo_echo",
      description: "d",
    });
    const fetchMock = vi.fn(async () =>
      Response.json({ jsonrpc: "2.0", result: { envelope: { id: "resp-1" } }, id: "rpc-1" }),
    );
    const client = {
      provider: new URL("http://localhost:8080/"),
      capabilities: ["urn:asap:cap:demo_echo"],
      fetch: fetchMock as typeof fetch,
    };
    const agent = await asapAsRemoteAgent(client, client.provider, { mode: "delegated" });

    const bag: AsapRemoteRunContext = {};
    const rc = new RunContext(bag);
    agent.emit("agent_start", rc, agent, []);

    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalled());

    const firstCall = fetchMock.mock.calls[0];
    expect(firstCall).toBeDefined();
    const [url, init] = firstCall as unknown as [string | URL, RequestInit];
    expect(String(url)).toContain("/asap");
    const body = typeof init.body === "string" ? JSON.parse(init.body) : {};
    expect(body.method).toBe("asap.send");
    expect(body.params?.envelope?.payload_type).toBe("task.request");
    expect(bag.lastAsapHandoffEnvelope?.payload_type).toBe("task.request");
  });

  it("captures envelope draft with configured mode on agent_start", async () => {
    describeCapabilityMock.mockResolvedValue({
      name: "demo_echo",
      description: "d",
    });
    const fetchMock = vi.fn(async () =>
      Response.json({ jsonrpc: "2.0", result: {}, id: "rpc-1" }),
    );
    const client = {
      provider: new URL("http://localhost:9999/"),
      capabilities: ["urn:asap:cap:demo_echo"],
      fetch: fetchMock as typeof fetch,
    };
    const agent = await asapAsRemoteAgent(client, "http://localhost:8080/", { mode: "delegated" });

    const bag: AsapRemoteRunContext = {};
    const rc = new RunContext(bag);
    agent.emit("agent_start", rc, agent, []);

    expect(bag.lastAsapHandoffEnvelope?.extensions).toEqual({ asap_agent_mode: "delegated" });
    expect((bag.lastAsapHandoffEnvelope?.recipient as string | undefined) ?? "").toContain("8080");
  });

  it("installs ASAP tools keyed like capabilityToolKey", async () => {
    describeCapabilityMock.mockResolvedValue({ name: "demo_echo", description: "Echo" });
    const client = {
      provider: new URL("http://localhost:8080/"),
      capabilities: ["urn:asap:cap:demo_echo"],
    };
    const agent = await asapAsRemoteAgent(client, client.provider);
    const enabled = await agent.getAllTools(new RunContext<AsapRemoteRunContext>({}));
    const names = enabled.map((t) => (t as { name?: string }).name).filter(Boolean);
    expect(names).toContain(capabilityToolKey("urn:asap:cap:demo_echo"));
  });

  it("relays executeCapability through bundled tools", async () => {
    describeCapabilityMock.mockResolvedValue({ name: "demo_echo", description: "d" });
    const spy = vi.spyOn(asapClient, "executeCapability").mockResolvedValue({ ok: true });
    const client = {
      provider: new URL("http://localhost:8080/"),
      capabilities: ["urn:asap:cap:demo_echo"],
      agentJwt: "jwt-handoff",
    };
    const agent = await asapAsRemoteAgent(client, client.provider);
    const enabled = await agent.getAllTools(new RunContext<AsapRemoteRunContext>({}));
    await invokeFunctionTool({
      tool: enabled[0] as FunctionTool,
      runContext: new RunContext({}),
      input: JSON.stringify({ message: "ping" }),
    });
    expect(spy).toHaveBeenCalledWith(
      client.provider,
      "urn:asap:cap:demo_echo",
      { message: "ping" },
      expect.objectContaining({ agentJwt: "jwt-handoff" }),
    );
  });
});
