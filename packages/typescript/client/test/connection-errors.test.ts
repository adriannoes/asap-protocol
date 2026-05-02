import { describe, expect, it, vi } from "vitest";

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

describe("connection error and branch paths", () => {
  it("connectAgent throws on invalid JSON and HTTP errors", async () => {
    const host = await createHost({ storage: new MemoryStorage() });
    const agent = await createAgent(host, { mode: "delegated" });

    const badJson = vi.fn().mockResolvedValue(new Response("{", { status: 200 }));
    await expect(
      connectAgent(new URL("https://p.example/"), host, agent, ["x"], "delegated", {
        audience: AUD,
        fetch: badJson as typeof fetch,
      }),
    ).rejects.toThrow(/invalid JSON/u);

    const httpErr = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "no room" }), { status: 429 }),
    );
    await expect(
      connectAgent(new URL("https://p.example/"), host, agent, ["x"], "delegated", {
        audience: AUD,
        fetch: httpErr as typeof fetch,
      }),
    ).rejects.toThrow(/connectAgent failed/u);

    const missingFields = vi.fn().mockResolvedValue(new Response(JSON.stringify({ agent_id: "a" }), { status: 200 }));
    await expect(
      connectAgent(new URL("https://p.example/"), host, agent, ["x"], "delegated", {
        audience: AUD,
        fetch: missingFields as typeof fetch,
      }),
    ).rejects.toThrow(/missing agent_id/u);
  });

  it("connectAgent includes approval_method and agent_controls_browser when set", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ agent_id: "ag", host_id: "hg", status: "pending" }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    const host = await createHost({ storage: new MemoryStorage() });
    const agent = await createAgent(host, { mode: "delegated" });
    await connectAgent(new URL("https://p.example/base/"), host, agent, ["c"], "delegated", {
      audience: AUD,
      approvalMethod: "device_authorization",
      agentControlsBrowser: true,
      fetch: fetchMock as typeof fetch,
    });
    const body = JSON.parse((fetchMock.mock.calls[0]?.[1] as RequestInit).body as string);
    expect(body.approval_method).toBe("device_authorization");
    expect(body.agent_controls_browser).toBe(true);
  });

  it("disconnectAgent and reactivateAgent surface invalid JSON and HTTP failures", async () => {
    const host = await createHost({ storage: new MemoryStorage() });

    const badDisc = vi.fn().mockResolvedValue(new Response("x", { status: 200 }));
    await expect(
      disconnectAgent(new URL("https://p.example/"), host, "a1", { audience: AUD, fetch: badDisc as typeof fetch }),
    ).rejects.toThrow(/invalid JSON/u);

    const reHttp = vi.fn().mockResolvedValue(new Response("{}", { status: 503 }));
    await expect(
      reactivateAgent(new URL("https://p.example/"), host, "a1", { audience: AUD, fetch: reHttp as typeof fetch }),
    ).rejects.toThrow(/reactivateAgent failed/u);

    const reBad = vi.fn().mockResolvedValue(new Response(JSON.stringify({ agent_id: "a" }), { status: 200 }));
    await expect(
      reactivateAgent(new URL("https://p.example/"), host, "a1", { audience: AUD, fetch: reBad as typeof fetch }),
    ).rejects.toThrow(/missing agent_id/u);
  });

  it("agentStatus throws on invalid grants and HTTP failures", async () => {
    const host = await createHost({ storage: new MemoryStorage() });
    const badGrant = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          agent_id: "a",
          host_id: "h",
          status: "active",
          capabilities: [{}],
        }),
        { status: 200 },
      ),
    );
    await expect(
      agentStatus(new URL("https://p.example/"), host, "a", { audience: AUD, fetch: badGrant as typeof fetch }),
    ).rejects.toThrow(/capabilities\[0\]/u);

    const stErr = vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "db" }), { status: 500 }));
    await expect(
      agentStatus(new URL("https://p.example/"), host, "a", { audience: AUD, fetch: stErr as typeof fetch }),
    ).rejects.toThrow(/agentStatus failed/u);
  });

  it("agentStatus parses lifecycle null fields and optional strings", async () => {
    const host = await createHost({ storage: new MemoryStorage() });
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          agent_id: "a",
          host_id: "h",
          status: "active",
          capabilities: [],
          lifecycle: {
            mode: "delegated",
            session_ttl: null,
            max_lifetime: null,
            absolute_lifetime: null,
            activated_at: null,
            last_used_at: null,
            created_at: "2026-01-01T00:00:00Z",
          },
          approval_status: "approved",
          deny_reason: "no",
        }),
        { status: 200 },
      ),
    );
    const st = await agentStatus(new URL("https://p.example/"), host, "a", {
      audience: AUD,
      fetch: fetchMock as typeof fetch,
    });
    expect(st.lifecycle?.session_ttl).toBeNull();
    expect(st.approvalStatus).toBe("approved");
    expect(st.denyReason).toBe("no");
  });

  it("requestCapability sends normalized specs and surfaces failures", async () => {
    const host = await createHost({ storage: new MemoryStorage() });
    const agent = await createAgent(host, { mode: "delegated" });

    const ok = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }));
    const out = await requestCapability(
      new URL("https://p.example/"),
      agent,
      ["plain", { name: "with", constraints: { max: 1 } }],
      { audience: AUD, fetch: ok as typeof fetch },
    );
    expect(out).toEqual({ ok: true });
    const body = JSON.parse((ok.mock.calls[0]?.[1] as RequestInit).body as string);
    expect(body.capabilities).toEqual(["plain", { name: "with", constraints: { max: 1 } }]);

    const bad = vi.fn().mockResolvedValue(new Response("{", { status: 200 }));
    await expect(
      requestCapability(new URL("https://p.example/"), agent, ["x"], {
        audience: AUD,
        fetch: bad as typeof fetch,
      }),
    ).rejects.toThrow(/invalid JSON/u);

    const http = vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: "nope" }), { status: 403 }));
    await expect(
      requestCapability(new URL("https://p.example/"), agent, ["x"], {
        audience: AUD,
        fetch: http as typeof fetch,
      }),
    ).rejects.toThrow(/requestCapability failed/u);

    const notObject = vi.fn().mockResolvedValue(new Response(JSON.stringify(null), { status: 200 }));
    await expect(
      requestCapability(new URL("https://p.example/"), agent, ["x"], {
        audience: AUD,
        fetch: notObject as typeof fetch,
      }),
    ).rejects.toThrow(/expected JSON object response body/u);
  });
});
