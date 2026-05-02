import { afterEach, describe, expect, it, vi } from "vitest";

import { LocalStorage } from "../src/storage-local.js";

describe("LocalStorage default backing", () => {
  const original = globalThis.localStorage;

  afterEach(() => {
    if (original === undefined) {
      Reflect.deleteProperty(globalThis, "localStorage");
    } else {
      Object.defineProperty(globalThis, "localStorage", {
        value: original,
        configurable: true,
        enumerable: true,
        writable: true,
      });
    }
    vi.restoreAllMocks();
  });

  it("throws when localStorage is missing from globalThis", () => {
    Reflect.deleteProperty(globalThis, "localStorage");
    expect(() => new LocalStorage("pfx:")).toThrow(/localStorage is not available/u);
  });

  it("throws when localStorage exists but is undefined", () => {
    Object.defineProperty(globalThis, "localStorage", {
      value: undefined,
      configurable: true,
      enumerable: true,
      writable: true,
    });
    expect(() => new LocalStorage("pfx:")).toThrow(/localStorage is not available/u);
  });
});
