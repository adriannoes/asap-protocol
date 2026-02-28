/**
 * Unit tests for ASAP OpenClaw Skill.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import defaultExport, {
  fetchRegistry,
  findEntryByUrn,
  getHttpEndpoint,
  invokeAsapAgent,
} from "./index";

const MOCK_REGISTRY_URL = "https://registry.example/registry.json";
const MOCK_AGENT_URN = "urn:asap:agent:test-agent";
const MOCK_HTTP_ENDPOINT = "https://agent.example.com/asap";

const MOCK_REGISTRY_RESPONSE = {
  agents: [
    {
      id: MOCK_AGENT_URN,
      name: "Test Agent",
      endpoints: { http: MOCK_HTTP_ENDPOINT, manifest: "https://agent.example.com/manifest.json" },
    },
    {
      id: "urn:asap:agent:other",
      name: "Other Agent",
      endpoints: { http: "https://other.example/asap" },
    },
  ],
};

const MOCK_AGENT_SUCCESS_RESPONSE = {
  jsonrpc: "2.0",
  id: "1",
  result: {
    envelope: {
      payload: { result: { output: "done" } },
    },
  },
};

describe("findEntryByUrn", () => {
  it("returns entry when URN exists", () => {
    const entry = findEntryByUrn(MOCK_REGISTRY_RESPONSE.agents as never[], MOCK_AGENT_URN);
    expect(entry).not.toBeNull();
    expect(entry?.id).toBe(MOCK_AGENT_URN);
  });

  it("returns null when URN not found", () => {
    const entry = findEntryByUrn(MOCK_REGISTRY_RESPONSE.agents as never[], "urn:asap:agent:missing");
    expect(entry).toBeNull();
  });

  it("returns null for empty agents list", () => {
    const entry = findEntryByUrn([], MOCK_AGENT_URN);
    expect(entry).toBeNull();
  });
});

describe("getHttpEndpoint", () => {
  it("returns http endpoint when present", () => {
    const entry = MOCK_REGISTRY_RESPONSE.agents[0] as never;
    expect(getHttpEndpoint(entry)).toBe(MOCK_HTTP_ENDPOINT);
  });

  it("throws when entry has no http endpoint", () => {
    const entry = { id: "urn:asap:agent:no-http", endpoints: {} } as never;
    expect(() => getHttpEndpoint(entry)).toThrow("has no HTTP endpoint");
  });

  it("throws when endpoints is undefined", () => {
    const entry = { id: "urn:asap:agent:no-endpoints" } as never;
    expect(() => getHttpEndpoint(entry)).toThrow("has no HTTP endpoint");
  });
});

describe("fetchRegistry", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url === MOCK_REGISTRY_URL) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(MOCK_REGISTRY_RESPONSE),
          } as Response);
        }
        return Promise.reject(new Error("Unexpected URL"));
      })
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns agents from registry", async () => {
    const agents = await fetchRegistry(MOCK_REGISTRY_URL);
    expect(agents).toHaveLength(2);
    expect(agents[0].id).toBe(MOCK_AGENT_URN);
  });

  it("returns empty array when registry has no agents", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve({}),
        } as Response)
      )
    );
    const agents = await fetchRegistry(MOCK_REGISTRY_URL);
    expect(agents).toEqual([]);
  });

  it("throws when registry fetch fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: false,
          status: 404,
          statusText: "Not Found",
        } as Response)
      )
    );
    await expect(fetchRegistry(MOCK_REGISTRY_URL)).rejects.toThrow("Registry fetch failed");
  });
});

describe("invokeAsapAgent", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn((_url: string, opts?: RequestInit) => {
        const body = opts?.body ? JSON.parse(opts.body as string) : {};
        if (body.method === "asap.send") {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(MOCK_AGENT_SUCCESS_RESPONSE),
          } as Response);
        }
        return Promise.reject(new Error("Unexpected request"));
      })
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("sends JSON-RPC with envelope and returns result", async () => {
    const result = await invokeAsapAgent(
      MOCK_HTTP_ENDPOINT,
      MOCK_AGENT_URN,
      "echo",
      { message: "hello" }
    );
    expect(result).toEqual({ output: "done" });
  });

  it("includes Authorization header when authToken provided", async () => {
    const fetchMock = vi.fn((_url: string, opts?: RequestInit) =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(MOCK_AGENT_SUCCESS_RESPONSE),
      } as Response)
    );
    vi.stubGlobal("fetch", fetchMock);

    await invokeAsapAgent(
      MOCK_HTTP_ENDPOINT,
      MOCK_AGENT_URN,
      "echo",
      {},
      "secret-token"
    );

    expect(fetchMock).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer secret-token",
        }),
      })
    );
  });

  it("throws when agent returns 4xx", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: false,
          status: 401,
          statusText: "Unauthorized",
        } as Response)
      )
    );
    await expect(
      invokeAsapAgent(MOCK_HTTP_ENDPOINT, MOCK_AGENT_URN, "echo", {})
    ).rejects.toThrow("ASAP agent request failed");
  });

  it("throws when agent returns JSON-RPC error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              jsonrpc: "2.0",
              error: { code: -32603, message: "Internal error" },
            }),
        } as Response)
      )
    );
    await expect(
      invokeAsapAgent(MOCK_HTTP_ENDPOINT, MOCK_AGENT_URN, "echo", {})
    ).rejects.toThrow("ASAP agent error");
  });
});

describe("asap_invoke tool execute", () => {
  let toolExecute: (id: string, params: { urn: string; skill: string; input?: Record<string, unknown> }) => Promise<{ content: { type: string; text: string }[] }>;

  beforeEach(() => {
    const tools: unknown[] = [];
    defaultExport({ registerTool: (t: unknown) => tools.push(t) });
    const tool = tools[0] as { execute: typeof toolExecute };
    toolExecute = tool.execute.bind(tool);

    vi.stubGlobal("fetch", vi.fn((url: string, opts?: RequestInit) => {
      if (url.includes("registry")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(MOCK_REGISTRY_RESPONSE),
        } as Response);
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(MOCK_AGENT_SUCCESS_RESPONSE),
      } as Response);
    }));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns success content when agent found and invoke succeeds", async () => {
    const result = await toolExecute("1", {
      urn: MOCK_AGENT_URN,
      skill: "echo",
      input: { x: "y" },
    });
    expect(result.content).toHaveLength(1);
    expect(result.content[0].type).toBe("text");
    expect(result.content[0].text).toContain("output");
    expect(result.content[0].text).toContain("done");
  });

  it("returns error content when agent not in registry", async () => {
    const result = await toolExecute("1", {
      urn: "urn:asap:agent:nonexistent",
      skill: "echo",
    });
    expect(result.content[0].text).toContain("Error:");
    expect(result.content[0].text).toContain("not found");
  });
});
