import { describe, expect, it, vi } from "vitest";

import { capabilityToolKey } from "@asap-protocol/client/adapters/shared";
import { createAsapMastraAgent } from "../src/asap-mastra-agent.js";

const describeCapabilityMock = vi.fn();

vi.mock("@asap-protocol/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@asap-protocol/client")>();
  return {
    ...actual,
    describeCapability: (...args: unknown[]) => describeCapabilityMock(...args),
  };
});

describe("createAsapMastraAgent", () => {
  it("exposes ASAP capabilities under deterministic Mastra tool keys", async () => {
    describeCapabilityMock.mockResolvedValue({ name: "demo_echo", description: "d" });
    const client = {
      provider: new URL("http://localhost:8080/"),
      capabilities: ["urn:asap:cap:demo_echo"],
    };
    const agent = await createAsapMastraAgent({
      client,
      capabilities: client.capabilities,
      model: "openai/gpt-4o-mini",
    });
    const tools = await agent.listTools();
    expect(Object.keys(tools)).toContain(capabilityToolKey("urn:asap:cap:demo_echo"));
  });

  it("registers one Mastra tool per capability", async () => {
    describeCapabilityMock.mockImplementation(async (_p, name: string) => ({
      name,
      description: "d",
    }));
    const caps = ["urn:asap:cap:echo", "urn:asap:cap:demo_other"];
    const client = {
      provider: new URL("http://localhost:8080/"),
      capabilities: caps,
    };
    const agent = await createAsapMastraAgent({
      client,
      capabilities: caps,
      model: "openai/gpt-4o-mini",
    });
    const tools = await agent.listTools();
    expect(Object.keys(tools).sort()).toEqual(
      [capabilityToolKey("urn:asap:cap:echo"), capabilityToolKey("urn:asap:cap:demo_other")].sort(),
    );
  });

  it("uses default instructions that reference configured capabilities", async () => {
    describeCapabilityMock.mockResolvedValue({ name: "alpha", description: "d" });
    const client = {
      provider: new URL("http://localhost:8080/"),
      capabilities: ["urn:asap:cap:alpha"],
    };
    const agent = await createAsapMastraAgent({
      client,
      capabilities: client.capabilities,
      model: "openai/gpt-4o-mini",
    });
    const instructions = await agent.getInstructions();
    expect(String(instructions)).toContain("urn:asap:cap:alpha");
    expect(String(instructions).toLowerCase()).toContain("asap");
  });

  it("honors custom instructions when provided", async () => {
    describeCapabilityMock.mockResolvedValue({ name: "alpha", description: "d" });
    const client = {
      provider: new URL("http://localhost:8080/"),
      capabilities: ["urn:asap:cap:alpha"],
    };
    const agent = await createAsapMastraAgent({
      client,
      capabilities: client.capabilities,
      model: "openai/gpt-4o-mini",
      instructions: "Custom system prompt only.",
    });
    expect(String(await agent.getInstructions())).toBe("Custom system prompt only.");
  });
});
