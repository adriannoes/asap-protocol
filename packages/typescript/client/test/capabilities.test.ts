import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  describeCapability,
  executeCapability,
  listCapabilities,
} from "../src/capabilities.js";
import { RecoverableError } from "../src/errors.js";

describe("capabilities", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("POSTs to the provider gateway with Agent JWT and returns the JSON-RPC result", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ jsonrpc: "2.0", id: 1, result: { ok: true } }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const result = await executeCapability(new URL("https://provider.example"), "echo", {
      x: 1,
    });

    expect(result).toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalled();
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(String(url)).toContain("/asap/capability/execute");
    expect(init.method).toBe("POST");
    expect(init.body).toBe(JSON.stringify({ capability: "echo", arguments: { x: 1 } }));
  });

  it("maps constraint_violated (403) to RecoverableError with violations", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          error: "constraint_violated",
          capability: "echo",
          violations: [{ field: "x", operator: "lte", message: "must be <= 10" }],
        }),
        { status: 403, headers: { "Content-Type": "application/json" } },
      ),
    );
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await expect(
      executeCapability(new URL("https://provider.example"), "echo", { x: 99 }),
    ).rejects.toSatisfy((err: unknown) => {
      expect(err).toBeInstanceOf(RecoverableError);
      expect(err).toMatchObject({
        code: "CONSTRAINT_VIOLATED",
        violations: [{ field: "x", operator: "lte", message: "must be <= 10" }],
      });
      return true;
    });
  });

  it("listCapabilities sends query params and unwraps JSON-RPC result", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          jsonrpc: "2.0",
          id: 1,
          result: {
            capabilities: [{ name: "echo", description: "Echo", location: "/x", grant_status: null }],
            next_cursor: 10,
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const result = await listCapabilities(new URL("https://provider.example/asap/"), {
      query: "echo",
      cursor: 2,
      limit: 5,
      agentJwt: "jwt-1",
      fetch: fetchMock,
    });

    expect(result.capabilities).toHaveLength(1);
    expect(result.capabilities[0]).toMatchObject({
      name: "echo",
      description: "Echo",
      location: "/x",
      grant_status: null,
    });
    expect(result.next_cursor).toBe(10);
    const url = String(fetchMock.mock.calls[0]?.[0]);
    expect(url).toContain("query=echo");
    expect(url).toContain("cursor=2");
    expect(url).toContain("limit=5");
  });

  it("listCapabilities rejects invalid JSON", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("not-json", { status: 200 }));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await expect(listCapabilities(new URL("https://p.example"))).rejects.toThrow(/invalid JSON/u);
  });

  it("listCapabilities rejects HTTP errors", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ error: "server" }), { status: 500 }),
    );
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await expect(listCapabilities(new URL("https://p.example"))).rejects.toThrow(/capability list failed/u);
  });

  it("listCapabilities rejects malformed payload", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ capabilities: "bad" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await expect(listCapabilities(new URL("https://p.example"))).rejects.toThrow(/expected capabilities array/u);
  });

  it("listCapabilities rejects Json-RPC error payloads", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          jsonrpc: "2.0",
          id: 1,
          error: { code: -32000, message: "boom" },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await expect(listCapabilities(new URL("https://p.example"))).rejects.toMatchObject({ name: "JsonRpcError" });
  });

  it("describeCapability returns schema fields", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          jsonrpc: "2.0",
          id: 1,
          result: {
            name: "echo",
            description: "Echo skill",
            input_schema: { type: "object" },
            output_schema: { type: "string" },
            location: "/cap",
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const d = await describeCapability(new URL("https://provider.example"), "echo", { fetch: fetchMock });
    expect(d).toMatchObject({
      name: "echo",
      description: "Echo skill",
      input_schema: { type: "object" },
      output_schema: { type: "string" },
      location: "/cap",
    });
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain("describe?name=echo");
  });

  it("describeCapability rejects HTTP errors and invalid bodies", async () => {
    const badStatus = vi.fn().mockResolvedValue(new Response("{}", { status: 404 }));
    globalThis.fetch = badStatus as unknown as typeof fetch;
    await expect(describeCapability(new URL("https://p.example"), "x")).rejects.toThrow(/describe failed/u);

    const badJson = vi.fn().mockResolvedValue(new Response("{", { status: 200 }));
    globalThis.fetch = badJson as unknown as typeof fetch;
    await expect(describeCapability(new URL("https://p.example"), "x")).rejects.toThrow(/invalid JSON/u);

    const badShape = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ jsonrpc: "2.0", result: { description: "only" } }), { status: 200 }),
    );
    globalThis.fetch = badShape as unknown as typeof fetch;
    await expect(describeCapability(new URL("https://p.example"), "x")).rejects.toThrow(/name and description/u);
  });

  it("executeCapability rejects invalid JSON and generic HTTP failures", async () => {
    const badJson = vi.fn().mockResolvedValue(new Response("{{{", { status: 200 }));
    globalThis.fetch = badJson as unknown as typeof fetch;
    await expect(executeCapability(new URL("https://p.example"), "echo", {})).rejects.toThrow(
      /capability execute: invalid JSON/u,
    );

    const detail = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "not allowed" }), { status: 401 }),
    );
    globalThis.fetch = detail as unknown as typeof fetch;
    await expect(executeCapability(new URL("https://p.example"), "echo", {})).rejects.toThrow(/401/u);

    const generic = vi.fn().mockResolvedValue(new Response(JSON.stringify({ z: 1 }), { status: 500 }));
    globalThis.fetch = generic as unknown as typeof fetch;
    await expect(executeCapability(new URL("https://p.example"), "echo", {})).rejects.toThrow(/500/u);
  });

  it("executeCapability unwraps Json-RPC error responses", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          jsonrpc: "2.0",
          id: 1,
          error: { code: -32603, message: "internal" },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await expect(executeCapability(new URL("https://p.example"), "echo", {})).rejects.toMatchObject({
      name: "JsonRpcError",
    });
  });
});
