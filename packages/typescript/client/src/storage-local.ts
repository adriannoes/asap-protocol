/**
 * Universal storage implementations (browser-safe).
 */

/** Async string key-value store for JWK material and similar secrets. */
export interface Storage {
  get(key: string): Promise<string | undefined>;
  set(key: string, value: string): Promise<void>;
  delete(key: string): Promise<void>;
}

export class MemoryStorage implements Storage {
  private readonly data = new Map<string, string>();

  async get(key: string): Promise<string | undefined> {
    return this.data.get(key);
  }

  async set(key: string, value: string): Promise<void> {
    this.data.set(key, value);
  }

  async delete(key: string): Promise<void> {
    this.data.delete(key);
  }
}

/** Subset of `Storage` used by `window.localStorage` (string values). */
export interface WebStorageLike {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

/**
 * Browser storage using `localStorage` (or a {@link WebStorageLike} for tests).
 *
 * All keys are prefixed to avoid collisions with unrelated site data.
 */
export class LocalStorage implements Storage {
  constructor(
    private readonly keyPrefix: string,
    private readonly backing: WebStorageLike = getDefaultLocalStorageBacking(),
  ) {}

  private namespaced(key: string): string {
    return `${this.keyPrefix}${key}`;
  }

  async get(key: string): Promise<string | undefined> {
    const v = this.backing.getItem(this.namespaced(key));
    return v === null ? undefined : v;
  }

  async set(key: string, value: string): Promise<void> {
    this.backing.setItem(this.namespaced(key), value);
  }

  async delete(key: string): Promise<void> {
    this.backing.removeItem(this.namespaced(key));
  }
}

function getDefaultLocalStorageBacking(): WebStorageLike {
  if (typeof globalThis === "undefined" || !("localStorage" in globalThis)) {
    throw new Error("localStorage is not available in this environment");
  }
  const ls = (globalThis as unknown as { localStorage?: WebStorageLike }).localStorage;
  if (ls === undefined) {
    throw new Error("localStorage is not available in this environment");
  }
  return ls;
}
