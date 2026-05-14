import http from "node:http";

import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";

import {
  DEFAULT_REGISTRY_URL,
  discoverProvider,
  listProviders,
  manifestUrlForBase,
  searchProviders,
  WELLKNOWN_MANIFEST_PATH,
} from "../src/discovery.js";

import type { LiteRegistry } from "../src/discovery.js";

const sampleRegistry: LiteRegistry = {
  version: "1.0",
  updated_at: "2026-01-01T00:00:00Z",
  agents: [
    {
      id: "urn:asap:agent:a",
      name: "Alpha Reviewer",
      description: "Does code review",
      endpoints: { http: "https://a.example/asap", manifest: "https://a.example/.well-known/asap/manifest.json" },
      skills: ["code_review"],
      category: "Coding",
      tags: ["review"],
      asap_version: "2.0.0",
    },
    {
      id: "urn:asap:agent:b",
      name: "Beta Bot",
      description: "Summaries only",
      endpoints: { http: "https://b.example/asap" },
      skills: ["summarize"],
      tags: [],
      asap_version: "2.0.0",
    },
  ],
};

const sampleManifest = {
  id: "urn:asap:agent:local-test",
  name: "Local Test Agent",
  version: "1.0.0",
  description: "Integration fixture",
  capabilities: {
    asap_version: "2.2",
    skills: [{ id: "echo", description: "Echo" }],
    state_persistence: false,
    streaming: false,
    mcp_tools: [],
  },
  endpoints: { asap: "http://127.0.0.1:9/asap", events: null },
  supported_versions: ["2.2"],
  ttl_seconds: 300,
};

describe("discovery (TS-002)", () => {
  it("listProviders parses registry JSON from fetch", async () => {
    const fetchMock = vi.fn(async () => {
      return new Response(JSON.stringify(sampleRegistry), { status: 200, headers: { "Content-Type": "application/json" } });
    });
    const reg = await listProviders("https://registry.example/registry.json", { fetch: fetchMock });
    expect(fetchMock).toHaveBeenCalledWith("https://registry.example/registry.json", expect.any(Object));
    expect(reg.version).toBe("1.0");
    expect(reg.agents).toHaveLength(2);
    expect(reg.agents[0]!.id).toBe("urn:asap:agent:a");
  });

  it("searchProviders filters by intent using an in-memory registry", async () => {
    const matches = await searchProviders("review", { registry: sampleRegistry });
    expect(matches.map((m) => m.id)).toEqual(["urn:asap:agent:a"]);
  });

  it("searchProviders returns empty for blank intent without fetching", async () => {
    const spy = vi.fn();
    await expect(searchProviders("   ", { fetch: spy as typeof fetch })).resolves.toEqual([]);
    expect(spy).not.toHaveBeenCalled();
  });

  it("searchProviders uses DEFAULT_REGISTRY_URL when resolving registry", async () => {
    const fetchMock = vi.fn(async () => {
      return new Response(JSON.stringify(sampleRegistry), { status: 200 });
    });
    await searchProviders("Beta", { fetch: fetchMock });
    expect(fetchMock).toHaveBeenCalledWith(DEFAULT_REGISTRY_URL, expect.any(Object));
  });

  it("discoverProvider requests well-known manifest URL", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      expect(String(input)).toBe("https://agent.example/.well-known/asap/manifest.json");
      return new Response(JSON.stringify(sampleManifest), { status: 200 });
    });
    const m = await discoverProvider("https://agent.example", { fetch: fetchMock });
    expect(m.id).toBe("urn:asap:agent:local-test");
    expect(m.endpoints.asap).toContain("127.0.0.1");
  });

  it("manifestUrlForBase strips trailing slashes before appending path", () => {
    expect(manifestUrlForBase("https://x.com")).toBe(`https://x.com${WELLKNOWN_MANIFEST_PATH}`);
    expect(manifestUrlForBase("https://x.com/sub/")).toBe(`https://x.com/sub${WELLKNOWN_MANIFEST_PATH}`);
  });
});

describe("discovery integration (local HTTP)", () => {
  const server = http.createServer((req, res) => {
    if (req.url?.endsWith(WELLKNOWN_MANIFEST_PATH)) {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify(sampleManifest));
      return;
    }
    res.writeHead(404);
    res.end();
  });

  beforeAll(
    () =>
      new Promise<void>((resolve, reject) => {
        server.listen(0, "127.0.0.1", () => resolve());
        server.on("error", reject);
      }),
  );

  afterAll(
    () =>
      new Promise<void>((resolve, reject) => {
        server.close((err) => (err ? reject(err) : resolve()));
      }),
  );

  it("discovers manifest from a real Node HTTP server", async () => {
    const addr = server.address();
    if (addr === null || typeof addr === "string") throw new Error("expected socket port");
    const base = `http://127.0.0.1:${String(addr.port)}/prefix`;
    const manifest = await discoverProvider(base);
    expect(manifest.name).toBe("Local Test Agent");
    expect(manifest.capabilities.skills[0]!.id).toBe("echo");
  });
});
