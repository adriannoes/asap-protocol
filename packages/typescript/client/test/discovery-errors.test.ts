import { describe, expect, it, vi } from "vitest";

import { discoverProvider, listProviders, searchProviders } from "../src/discovery.js";

import type { LiteRegistry } from "../src/discovery.js";

const minimalRegistry: LiteRegistry = {
  version: "1",
  updated_at: "2026-01-01T00:00:00Z",
  agents: [],
};

describe("discovery error paths", () => {
  it("listProviders throws on HTTP failure", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 502 }));
    await expect(listProviders("https://r.example/x.json", { fetch: fetchMock as typeof fetch })).rejects.toThrow(
      /registry request failed/u,
    );
  });

  it("listProviders surfaces JSON parse errors from response.json()", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: vi.fn().mockRejectedValue(new Error("truncated")),
    });
    await expect(listProviders("https://r.example/x.json", { fetch: fetchMock as typeof fetch })).rejects.toThrow(
      /invalid JSON \(truncated\)/u,
    );
  });

  it("listProviders throws when JSON is not an object", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(`"x"`, { status: 200 }));
    await expect(listProviders("https://r.example/x.json", { fetch: fetchMock as typeof fetch })).rejects.toThrow(
      /registry: expected a JSON object/u,
    );
  });

  it("discoverProvider throws on HTTP error and invalid manifest", async () => {
    const badHttp = vi.fn().mockResolvedValue(new Response("{}", { status: 404 }));
    await expect(discoverProvider("https://agent.example", { fetch: badHttp as typeof fetch })).rejects.toThrow(
      /manifest request failed/u,
    );

    const badJson = vi.fn().mockResolvedValue(new Response(`"oops"`, { status: 200 }));
    await expect(discoverProvider("https://agent.example", { fetch: badJson as typeof fetch })).rejects.toThrow(
      /manifest: expected a JSON object/u,
    );

    const incomplete = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: "x" }), { status: 200, headers: { "Content-Type": "application/json" } }),
    );
    await expect(discoverProvider("https://agent.example", { fetch: incomplete as typeof fetch })).rejects.toThrow(
      /missing name/u,
    );
  });

  it("searchProviders uses registryUrl when provided", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(minimalRegistry), { status: 200, headers: { "Content-Type": "application/json" } }),
    );
    await searchProviders("any", {
      registryUrl: "https://custom/registry.json",
      fetch: fetchMock as typeof fetch,
    });
    expect(fetchMock).toHaveBeenCalledWith("https://custom/registry.json", expect.any(Object));
  });
});
