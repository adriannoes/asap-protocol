import http from "node:http";

import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";

import {
  agentStatus,
  connectAgent,
  disconnectAgent,
  reactivateAgent,
  requestCapability,
} from "../src/connection.js";
import { createAgent, createHost } from "../src/identity.js";
import { MemoryStorage } from "../src/storage-local.js";

const AUD = "https://provider.example/gateway";

describe("connection (TS-004 / TS-005) — unit", () => {
  it("connectAgent POSTs register with Host JWT and agent public key claim path", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          agent_id: "agent_x",
          host_id: "urn:asap:host:y",
          status: "active",
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    const storage = new MemoryStorage();
    const host = await createHost({ storage });
    const agent = await createAgent(host, { mode: "delegated" });
    const result = await connectAgent(new URL("https://provider.example/base/"), host, agent, ["exec:read"], "delegated", {
      audience: AUD,
      fetch: fetchMock,
    });
    expect(result).toMatchObject({ agentId: "agent_x", hostId: "urn:asap:host:y", status: "active" });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(String(url)).toContain("/asap/agent/register");
    expect(init.method).toBe("POST");
    expect(init.headers).toMatchObject(expect.objectContaining({ Authorization: expect.stringMatching(/^Bearer /u) }));
    const body = JSON.parse(init.body as string);
    expect(body.capabilities).toEqual(["exec:read"]);
    expect(body.mode).toBe("delegated");
  });

  it("disconnectAgent POSTs revoke", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ agent_id: "a1", status: "revoked" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const host = await createHost({ storage: new MemoryStorage() });
    const out = await disconnectAgent(new URL("https://p.example/"), host, "a1", {
      audience: AUD,
      fetch: fetchMock,
    });
    expect(out).toEqual({ agentId: "a1", status: "revoked" });
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(String(url)).toContain("/asap/agent/revoke");
    expect(JSON.parse(init.body as string)).toEqual({ agent_id: "a1" });
  });

  it("agentStatus GETs with query agent_id", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          agent_id: "a1",
          host_id: "h1",
          status: "active",
          capabilities: [{ capability: "exec:read", status: "active" }],
          lifecycle: { mode: "delegated", created_at: "2026-01-01T00:00:00Z" },
        }),
        { status: 200 },
      ),
    );
    const host = await createHost({ storage: new MemoryStorage() });
    const st = await agentStatus(new URL("https://p.example/prefix/"), host, "a1", {
      audience: AUD,
      fetch: fetchMock,
    });
    expect(st.agentId).toBe("a1");
    expect(st.capabilities[0]?.capability).toBe("exec:read");
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(String(url)).toContain("agent_id=a1");
    expect(String(url)).toContain("/asap/agent/status");
  });

  it("reactivateAgent POSTs reactivate", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          agent_id: "a1",
          status: "active",
          capabilities: [{ capability: "exec:read", status: "active" }],
        }),
        { status: 200 },
      ),
    );
    const host = await createHost({ storage: new MemoryStorage() });
    const r = await reactivateAgent(new URL("https://p.example/"), host, "a1", { audience: AUD, fetch: fetchMock });
    expect(r.agentId).toBe("a1");
    expect(String(fetchMock.mock.calls[0]![0])).toContain("/asap/agent/reactivate");
  });

  it("requestCapability POSTs with Agent JWT", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: "pending", approval: { method: "device_authorization" } }), {
        status: 200,
      }),
    );
    const storage = new MemoryStorage();
    const host = await createHost({ storage });
    const agent = await createAgent(host, { mode: "delegated" });
    const receipt = await requestCapability(
      new URL("https://p.example/"),
      agent,
      ["new:cap", { name: "other", constraints: { max: 1 } }],
      { audience: AUD, fetch: fetchMock },
    );
    expect(receipt).toMatchObject({ status: "pending" });
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.headers).toMatchObject(expect.objectContaining({ Authorization: expect.stringMatching(/^Bearer /u) }));
    expect(JSON.parse(init.body as string)).toEqual({
      capabilities: ["new:cap", { name: "other", constraints: { max: 1 } }],
    });
  });
});

/** Minimal ASAP-compatible HTTP server for integration coverage. */
function startMockAsapServer(): Promise<{ baseUrl: URL; close: () => Promise<void> }> {
  type AgentRec = { status: "active" | "revoked"; hostId: string };
  const agents = new Map<string, AgentRec>();
  let counter = 0;

  const server = http.createServer((req, res) => {
    const url = new URL(req.url ?? "/", "http://127.0.0.1");
    const path = url.pathname;

    const sendJson = (code: number, obj: unknown): void => {
      res.writeHead(code, { "Content-Type": "application/json" });
      res.end(JSON.stringify(obj));
    };

    const auth = req.headers.authorization;
    if (!auth?.startsWith("Bearer ")) {
      sendJson(401, { detail: "Authentication required" });
      return;
    }

    if (req.method === "POST" && path.endsWith("/asap/agent/register")) {
      let _buf = "";
      req.on("data", (c) => {
        _buf += c;
      });
      req.on("end", () => {
        counter += 1;
        const agentId = `agent_integration_${String(counter)}`;
        const hostId = "urn:asap:host:integration";
        agents.set(agentId, { status: "active", hostId });
        sendJson(200, {
          agent_id: agentId,
          host_id: hostId,
          status: "active",
          agent_capability_grants: [],
        });
      });
      return;
    }

    if (req.method === "GET" && path.includes("/asap/agent/status")) {
      const aid = url.searchParams.get("agent_id");
      if (!aid || !agents.has(aid)) {
        sendJson(404, { detail: "unknown agent_id" });
        return;
      }
      const rec = agents.get(aid)!;
      sendJson(200, {
        agent_id: aid,
        host_id: rec.hostId,
        status: rec.status,
        capabilities: [],
        lifecycle: { mode: "delegated", created_at: "2026-01-01T00:00:00Z" },
      });
      return;
    }

    if (req.method === "POST" && path.endsWith("/asap/agent/revoke")) {
      let _buf = "";
      req.on("data", (c) => {
        _buf += c;
      });
      req.on("end", () => {
        const body = JSON.parse(_buf) as { agent_id?: string };
        const aid = body.agent_id;
        if (typeof aid !== "string" || !agents.has(aid)) {
          sendJson(404, { detail: "unknown agent_id" });
          return;
        }
        agents.set(aid, { ...agents.get(aid)!, status: "revoked" });
        sendJson(200, { agent_id: aid, status: "revoked" });
      });
      return;
    }

    if (req.method === "POST" && path.endsWith("/asap/agent/reactivate")) {
      let _buf = "";
      req.on("data", (c) => {
        _buf += c;
      });
      req.on("end", () => {
        const body = JSON.parse(_buf) as { agent_id?: string };
        const aid = body.agent_id;
        if (typeof aid !== "string" || !agents.has(aid)) {
          sendJson(404, { detail: "unknown agent_id" });
          return;
        }
        agents.set(aid, { ...agents.get(aid)!, status: "active" });
        sendJson(200, {
          agent_id: aid,
          status: "active",
          capabilities: [{ capability: "default", status: "active" }],
        });
      });
      return;
    }

    if (req.method === "POST" && path.endsWith("/asap/agent/request-capability")) {
      sendJson(200, { status: "pending", approval: { method: "device_authorization" } });
      return;
    }

    sendJson(404, { detail: "not found" });
  });

  return new Promise((resolve, reject) => {
    server.listen(0, "127.0.0.1", () => {
      const addr = server.address();
      if (addr === null || typeof addr === "string") {
        reject(new Error("no port"));
        return;
      }
      const baseUrl = new URL(`http://127.0.0.1:${String(addr.port)}/v1/`);
      resolve({
        baseUrl,
        close: () =>
          new Promise<void>((res, rej) => {
            server.close((err) => (err ? rej(err) : res()));
          }),
      });
    });
    server.on("error", reject);
  });
}

describe("connection — integration (minimal ASAP server)", () => {
  let baseUrl: URL;
  let close: () => Promise<void>;

  beforeAll(async () => {
    const s = await startMockAsapServer();
    baseUrl = s.baseUrl;
    close = s.close;
  });

  afterAll(async () => {
    await close();
  });

  it("runs register → status → requestCapability → revoke → reactivate", async () => {
    const storage = new MemoryStorage();
    const host = await createHost({ storage });
    const agent = await createAgent(host, { mode: "delegated" });

    const conn = await connectAgent(baseUrl, host, agent, ["exec:read"], "delegated", {
      audience: AUD,
    });
    expect(conn.status).toBe("active");

    const st = await agentStatus(baseUrl, host, conn.agentId, { audience: AUD });
    expect(st.status).toBe("active");

    const escal = await requestCapability(baseUrl, agent, ["extra:write"], { audience: AUD });
    expect(escal).toMatchObject({ status: "pending" });

    const disc = await disconnectAgent(baseUrl, host, conn.agentId, { audience: AUD });
    expect(disc.status).toBe("revoked");

    const st2 = await agentStatus(baseUrl, host, conn.agentId, { audience: AUD });
    expect(st2.status).toBe("revoked");

    const react = await reactivateAgent(baseUrl, host, conn.agentId, { audience: AUD });
    expect(react.status).toBe("active");
    expect(react.capabilities.length).toBeGreaterThan(0);
  });
});
