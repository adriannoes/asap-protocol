import { decodeProtectedHeader, importJWK, jwtVerify } from "jose";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { generateEd25519KeyPair, resetEd25519KeygenProbeForTests } from "../src/ed25519-keypair.js";
import { createAgent, createHost } from "../src/identity.js";
import { MemoryStorage } from "../src/storage-local.js";

describe("Ed25519 keygen (task 2.2)", () => {
  beforeEach(() => {
    resetEd25519KeygenProbeForTests();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    resetEd25519KeygenProbeForTests();
  });

  it("uses Web Crypto when subtle.generateKey succeeds", async () => {
    const spy = vi.spyOn(crypto.subtle, "generateKey");
    const storage = new MemoryStorage();
    const host = await createHost({ storage });
    expect(spy).toHaveBeenCalled();
    const token = await host.signHostJwt({ aud: "urn:asap:test:subtle-path" });
    const header = decodeProtectedHeader(token);
    expect(header.alg).toBe("EdDSA");
    const key = await importJWK(host.publicJwk, "EdDSA");
    await expect(
      jwtVerify(token, key, {
        algorithms: ["EdDSA", "Ed25519"],
        issuer: host.hostThumbprint,
        audience: "urn:asap:test:subtle-path",
      }),
    ).resolves.toBeTruthy();
  });

  it("falls back to @noble/ed25519 when subtle.generateKey rejects", async () => {
    vi.spyOn(crypto.subtle, "generateKey").mockRejectedValue(new Error("Ed25519 generateKey unsupported"));
    const storage = new MemoryStorage();
    const host = await createHost({ storage });
    const token = await host.signHostJwt({ aud: "urn:asap:test:noble-path" });
    const key = await importJWK(host.publicJwk, "EdDSA");
    await expect(
      jwtVerify(token, key, {
        algorithms: ["EdDSA", "Ed25519"],
        issuer: host.hostThumbprint,
        audience: "urn:asap:test:noble-path",
      }),
    ).resolves.toBeTruthy();
  });

  it("signs Agent JWT on noble path when subtle.generateKey rejects", async () => {
    vi.spyOn(crypto.subtle, "generateKey").mockRejectedValue(new Error("Ed25519 generateKey unsupported"));
    const storage = new MemoryStorage();
    const host = await createHost({ storage });
    const agent = await createAgent(host, { mode: "delegated" });
    const token = await agent.signAgentJwt({ aud: "urn:asap:test:noble-agent" });
    const key = await importJWK(agent.publicJwk, "EdDSA");
    await expect(
      jwtVerify(token, key, {
        algorithms: ["EdDSA", "Ed25519"],
        issuer: host.hostThumbprint,
        subject: agent.agentId,
        audience: "urn:asap:test:noble-agent",
      }),
    ).resolves.toBeTruthy();
  });

  it("caches generateKey failure: further keypairs skip subtle.generateKey", async () => {
    const spy = vi.spyOn(crypto.subtle, "generateKey").mockRejectedValue(
      new Error("Ed25519 generateKey unsupported"),
    );
    await createHost({ storage: new MemoryStorage() });
    await createHost({ storage: new MemoryStorage() });
    expect(spy).toHaveBeenCalledTimes(1);
  });

  it("when subtle path was cached as working but generateKey later fails, uses noble fallback", async () => {
    const realPair = await crypto.subtle.generateKey({ name: "Ed25519" }, true, ["sign", "verify"]);
    const spy = vi
      .spyOn(crypto.subtle, "generateKey")
      .mockResolvedValueOnce(realPair as CryptoKeyPair)
      .mockRejectedValueOnce(new Error("transient subtle failure"));
    const first = await generateEd25519KeyPair();
    const second = await generateEd25519KeyPair();
    expect(first.privateKey.algorithm.name).toBe("Ed25519");
    expect(second.privateKey.algorithm.name).toBe("Ed25519");
    expect(spy).toHaveBeenCalledTimes(2);
  });
});
