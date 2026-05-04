/**
 * OS keychain storage via optional `keytar` peer dependency.
 */

/// <reference path="../keytar.d.ts" />

import type { Storage } from "./storage-local.js";

function normalizeKeychainModule(m: unknown): KeychainLike {
  const rec = m as Record<string, unknown>;
  if (rec !== null && typeof rec.getPassword === "function") {
    return m as unknown as KeychainLike;
  }
  const def = rec?.default as Record<string, unknown> | undefined;
  if (def !== null && def !== undefined && typeof def.getPassword === "function") {
    return def as unknown as KeychainLike;
  }
  throw new Error("keytar module does not expose a compatible KeychainLike API");
}

/** Minimal surface of `keytar` used by {@link KeychainStorage}. */
export interface KeychainLike {
  getPassword(service: string, account: string): Promise<string | null>;
  setPassword(service: string, account: string, password: string): Promise<void>;
  deletePassword(service: string, account: string): Promise<boolean>;
}

async function keyToKeychainAccount(key: string): Promise<string> {
  if (key.length <= 200) {
    return key;
  }
  const digest = new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(key)));
  return `sha256:${hex(digest)}`;
}

function hex(bytes: Uint8Array): string {
  return [...bytes].map((b) => b.toString(16).padStart(2, "0")).join("");
}

/** OS keychain / credential store (optional `keytar` peer dependency). */
export class KeychainStorage implements Storage {
  private constructor(
    private readonly service: string,
    private readonly keychain: KeychainLike,
  ) {}

  /**
   * Builds storage backed by the real `keytar` module when installed; otherwise `undefined`.
   */
  static async tryCreate(opts: { readonly service: string }): Promise<KeychainStorage | undefined> {
    try {
      const keytar = await import("keytar");
      const mod = normalizeKeychainModule(keytar);
      return new KeychainStorage(opts.service, mod);
    } catch {
      return undefined;
    }
  }

  /** For tests or custom credential backends without loading `keytar`. */
  static withKeychain(opts: { readonly service: string; readonly keychain: KeychainLike }): KeychainStorage {
    return new KeychainStorage(opts.service, opts.keychain);
  }

  async get(key: string): Promise<string | undefined> {
    const account = await keyToKeychainAccount(key);
    const v = await this.keychain.getPassword(this.service, account);
    return v === null ? undefined : v;
  }

  async set(key: string, value: string): Promise<void> {
    const account = await keyToKeychainAccount(key);
    await this.keychain.setPassword(this.service, account, value);
  }

  async delete(key: string): Promise<void> {
    const account = await keyToKeychainAccount(key);
    await this.keychain.deletePassword(this.service, account);
  }
}
