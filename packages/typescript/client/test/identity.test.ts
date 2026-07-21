import { decodeProtectedHeader, importJWK, jwtVerify } from "jose";
import { describe, expect, it } from "vitest";
import {
  AGENT_JWT_TYP,
  HOST_JWT_TYP,
  createAgent,
  createHost,
  jwkThumbprintSha256,
  resumeAgent,
  resumeHost,
} from "../src/identity.js";
import { MemoryStorage } from "../src/storage-local.js";

describe("identity", () => {
  it("creates a host with persisted Ed25519 material", async () => {
    const storage = new MemoryStorage();
    const host = await createHost({ storage });
    expect(host).toMatchObject({
      hostId: expect.stringMatching(/^host_/u),
    });
    expect(host.hostThumbprint).toMatch(/^[A-Za-z0-9_-]+$/u);
    expect(host.publicJwk.kty).toBe("OKP");
    expect(host.publicJwk.crv).toBe("Ed25519");
    expect(host.publicJwk.d).toBeUndefined();
  });

  it("round-trips a Host JWT via jose (EdDSA, typ host+jwt)", async () => {
    const storage = new MemoryStorage();
    const host = await createHost({ storage });
    const aud = "urn:asap:test:audience";
    const token = await host.signHostJwt({ aud });

    const header = decodeProtectedHeader(token);
    expect(header.alg).toBe("EdDSA");
    expect(header.typ).toBe(HOST_JWT_TYP);

    const key = await importJWK(host.publicJwk, "EdDSA");
    const { payload } = await jwtVerify(token, key, {
      algorithms: ["EdDSA", "Ed25519"],
      issuer: host.hostThumbprint,
      audience: aud,
    });

    expect(payload.iss).toBe(host.hostThumbprint);
    expect(payload.host_public_key).toEqual({
      crv: "Ed25519",
      kty: "OKP",
      x: host.publicJwk.x,
    });
    const tp = await jwkThumbprintSha256(
      payload.host_public_key as Record<string, unknown>,
    );
    expect(tp).toBe(host.hostThumbprint);
  });

  it("round-trips an Agent JWT via jose (EdDSA, typ agent+jwt)", async () => {
    const storage = new MemoryStorage();
    const host = await createHost({ storage });
    const agent = await createAgent(host, { mode: "delegated" });
    const aud = "urn:asap:test:gateway";

    const token = await agent.signAgentJwt({
      aud,
      capabilities: ["urn:asap:cap:echo"],
    });

    const header = decodeProtectedHeader(token);
    expect(header.typ).toBe(AGENT_JWT_TYP);

    const key = await importJWK(agent.publicJwk, "EdDSA");
    const { payload } = await jwtVerify(token, key, {
      algorithms: ["EdDSA", "Ed25519"],
      issuer: host.hostThumbprint,
      subject: agent.agentId,
      audience: aud,
    });

    expect(payload.sub).toBe(agent.agentId);
    expect(payload.iss).toBe(host.hostThumbprint);
    expect(payload.capabilities).toEqual(["urn:asap:cap:echo"]);
  });

  it("embeds agent public key in Host JWT when requested", async () => {
    const storage = new MemoryStorage();
    const host = await createHost({ storage });
    const agent = await createAgent(host, { mode: "autonomous" });

    const token = await host.signHostJwt({
      aud: "urn:asap:test",
      agentPublicKey: agent.publicJwk,
    });

    const key = await importJWK(host.publicJwk, "EdDSA");
    const { payload } = await jwtVerify(token, key, {
      algorithms: ["EdDSA", "Ed25519"],
      issuer: host.hostThumbprint,
      audience: "urn:asap:test",
    });

    expect(payload.agent_public_key).toEqual({
      crv: "Ed25519",
      kty: "OKP",
      x: agent.publicJwk.x,
    });
  });

  it("resumeHost and resumeAgent restore signing material from storage", async () => {
    const storage = new MemoryStorage();
    const host = await createHost({ storage });
    const agent = await createAgent(host, { mode: "delegated" });

    const hostAgain = await resumeHost({ storage, hostId: host.hostId });
    const agentAgain = await resumeAgent(hostAgain, { agentId: agent.agentId, mode: "delegated" });

    expect(hostAgain.hostThumbprint).toBe(host.hostThumbprint);
    expect(agentAgain.agentId).toBe(agent.agentId);

    const aud = "urn:asap:test:resume";
    const key = await importJWK(agent.publicJwk, "EdDSA");
    const token = await agentAgain.signAgentJwt({ aud, capabilities: ["urn:asap:cap:x"] });
    await jwtVerify(token, key, {
      algorithms: ["EdDSA", "Ed25519"],
      issuer: host.hostThumbprint,
      audience: aud,
      subject: agent.agentId,
    });
  });
});
