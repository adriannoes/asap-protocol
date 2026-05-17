import { beforeEach, describe, expect, it, vi } from "vitest";

import * as clientApi from "@asap-protocol/client";
import { capabilityToolKey } from "@asap-protocol/client/adapters/shared";
import { ApprovalRequiredError, CapabilityNotGrantedError } from "../src/errors.js";
import { asapToolsForMastra } from "../src/asap-to-mastra-tool.js";

describe("asapToolsForMastra", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("returns one Mastra tool per configured capability", () => {
    const client = {
      provider: new URL("http://localhost:8080/"),
      capabilities: ["urn:asap:cap:demo_echo"],
    };
    const tools = asapToolsForMastra(client);
    expect(tools).toHaveLength(1);
    const tool = tools[0] as { id: string };
    expect(tool.id).toBe(capabilityToolKey("urn:asap:cap:demo_echo"));
  });

  it("routes tool execution to executeCapability with provider, name, args, and options", async () => {
    const spy = vi.spyOn(clientApi, "executeCapability").mockResolvedValue({ ok: true });
    const client = {
      provider: new URL("http://localhost:8080/"),
      capabilities: ["urn:asap:cap:demo_echo"],
      agentJwt: "jwt-test",
    };
    const tools = asapToolsForMastra(client);
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

  it("throws ApprovalRequiredError when the provider returns approval_required (403)", async () => {
    const fetchMock = vi.fn(async () => {
      return new Response(
        JSON.stringify({
          error: {
            code: "approval_required",
            message: "human approval pending",
            data: { reason: "policy" },
          },
        }),
        { status: 403 },
      );
    });
    const client = {
      provider: new URL("http://localhost:8080/"),
      capabilities: ["urn:asap:cap:demo_echo"],
      fetch: fetchMock,
    };
    const tools = asapToolsForMastra(client);
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
    const fetchMock = vi.fn(async () => {
      return new Response(
        JSON.stringify({
          error: {
            code: "capability_not_granted",
            message: "no grant",
            data: { required_capability: "file:read" },
            request_id: "req-1",
          },
        }),
        { status: 403 },
      );
    });
    const client = {
      provider: new URL("http://localhost:8080/"),
      capabilities: ["file:read"],
      fetch: fetchMock,
    };
    const tools = asapToolsForMastra(client, { requestCapability });
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
});
