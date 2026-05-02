import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

import { LocalStorage, MemoryStorage, type Storage, type WebStorageLike } from "../src/storage-local.js";
import { FileStorage } from "../src/storage-file.js";
import { KeychainStorage, type KeychainLike } from "../src/storage-keychain.js";

function describeKvStorageContract(
  label: string,
  setup: () => Promise<{ readonly storage: Storage; readonly teardown?: () => Promise<void> }>,
): void {
  describe(label, () => {
    let storage!: Storage;
    let teardown: (() => Promise<void>) | undefined;

    beforeEach(async () => {
      const ctx = await setup();
      storage = ctx.storage;
      teardown = ctx.teardown;
    });

    afterEach(async () => {
      await teardown?.();
    });

    it("returns undefined for missing keys", async () => {
      expect(await storage.get("asap/v2/host/x/missing")).toBeUndefined();
    });

    it("round-trips set, get, delete", async () => {
      const key = "asap/v2/host/h1/ed25519-private.jwk.json";
      await storage.set(key, '{"kty":"OKP"}');
      expect(await storage.get(key)).toBe('{"kty":"OKP"}');
      await storage.delete(key);
      expect(await storage.get(key)).toBeUndefined();
    });

    it("isolates distinct keys", async () => {
      await storage.set("a/b", "1");
      await storage.set("a/c", "2");
      expect(await storage.get("a/b")).toBe("1");
      expect(await storage.get("a/c")).toBe("2");
      await storage.delete("a/b");
      expect(await storage.get("a/b")).toBeUndefined();
      expect(await storage.get("a/c")).toBe("2");
      await storage.delete("a/c");
    });
  });
}

describeKvStorageContract("MemoryStorage", async () => ({
  storage: new MemoryStorage(),
}));

describeKvStorageContract("FileStorage", async () => {
  const dir = await mkdtemp(path.join(tmpdir(), "asap-file-storage-"));
  return {
    storage: new FileStorage(dir),
    teardown: async () => {
      await rm(dir, { recursive: true, force: true });
    },
  };
});

describeKvStorageContract("LocalStorage (WebStorageLike mock)", async () => {
  const map = new Map<string, string>();
  const mock: WebStorageLike = {
    getItem(k) {
      return map.has(k) ? map.get(k)! : null;
    },
    setItem(k, v) {
      map.set(k, v);
    },
    removeItem(k) {
      map.delete(k);
    },
  };
  return { storage: new LocalStorage("asap-test:", mock) };
});

describeKvStorageContract("KeychainStorage (in-memory KeychainLike)", async () => {
  const passwords = new Map<string, string>();
  const service = "asap-test-service";
  const keychain: KeychainLike = {
    async getPassword(serv, account) {
      return passwords.get(`${serv}::${account}`) ?? null;
    },
    async setPassword(serv, account, password) {
      passwords.set(`${serv}::${account}`, password);
    },
    async deletePassword(serv, account) {
      return passwords.delete(`${serv}::${account}`);
    },
  };
  return { storage: KeychainStorage.withKeychain({ service, keychain }) };
});

describe("KeychainStorage long keys", () => {
  it("uses a hashed account label when the logical key exceeds 200 characters", async () => {
    const accounts: string[] = [];
    const service = "asap-long-key";
    const keychain: KeychainLike = {
      async getPassword(serv, account) {
        expect(serv).toBe(service);
        accounts.push(account);
        return null;
      },
      async setPassword() {
        /* unused */
      },
      async deletePassword() {
        return false;
      },
    };
    const storage = KeychainStorage.withKeychain({ service, keychain });
    const longKey = `asap/${"x".repeat(220)}`;
    await storage.get(longKey);
    expect(accounts[0]).toMatch(/^sha256:[a-f0-9]{64}$/u);
  });
});
