import { keygenAsync } from "@noble/ed25519";

/**
 * Cached result of probing `crypto.subtle.generateKey({ name: "Ed25519" })`.
 * `undefined` = not yet probed; tests call {@link resetEd25519KeygenProbeForTests} after mocks.
 */
let subtleGenerateKeyWorks: boolean | undefined;

/** Clear probe cache (Vitest: call after mocking `crypto.subtle.generateKey`). */
export function resetEd25519KeygenProbeForTests(): void {
  subtleGenerateKeyWorks = undefined;
}

function b64urlRaw(data: Uint8Array): string {
  let bin = "";
  for (let i = 0; i < data.length; i += 1) {
    bin += String.fromCharCode(data[i]!);
  }
  const b64 = btoa(bin);
  return b64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/u, "");
}

async function trySubtleGenerateKeyPair(): Promise<CryptoKeyPair | null> {
  try {
    return await crypto.subtle.generateKey({ name: "Ed25519" }, true, ["sign", "verify"]);
  } catch {
    return null;
  }
}

async function generateNobleBackedCryptoKeyPair(): Promise<CryptoKeyPair> {
  const { secretKey, publicKey: rawPublicBytes } = await keygenAsync();
  const d = b64urlRaw(secretKey);
  const x = b64urlRaw(rawPublicBytes);
  const privateJwk: JsonWebKey = {
    kty: "OKP",
    crv: "Ed25519",
    d,
    x,
  };
  const publicJwk: JsonWebKey = {
    kty: "OKP",
    crv: "Ed25519",
    x,
  };
  const privateKey = (await crypto.subtle.importKey("jwk", privateJwk, { name: "Ed25519" }, true, [
    "sign",
  ])) as CryptoKey;
  const publicKeyCrypto = (await crypto.subtle.importKey(
    "jwk",
    publicJwk,
    { name: "Ed25519" },
    true,
    ["verify"],
  )) as CryptoKey;
  return { privateKey, publicKey: publicKeyCrypto };
}

/**
 * Generate an Ed25519 key pair: Web Crypto when supported, otherwise `@noble/ed25519`
 * material imported into `CryptoKey` for `jose` signing.
 */
export async function generateEd25519KeyPair(): Promise<CryptoKeyPair> {
  if (subtleGenerateKeyWorks === true) {
    const pair = await trySubtleGenerateKeyPair();
    if (pair !== null) {
      return pair;
    }
    subtleGenerateKeyWorks = false;
    return generateNobleBackedCryptoKeyPair();
  }
  if (subtleGenerateKeyWorks === false) {
    return generateNobleBackedCryptoKeyPair();
  }
  const pair = await trySubtleGenerateKeyPair();
  if (pair !== null) {
    subtleGenerateKeyWorks = true;
    return pair;
  }
  subtleGenerateKeyWorks = false;
  return generateNobleBackedCryptoKeyPair();
}
