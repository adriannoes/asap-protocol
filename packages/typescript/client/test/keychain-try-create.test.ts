import { describe, expect, it } from "vitest";

import { KeychainStorage } from "../src/storage-keychain.js";

describe("KeychainStorage.tryCreate", () => {
  it("returns storage when keytar resolves", async () => {
    const ks = await KeychainStorage.tryCreate({ service: "asap-alias-test" });
    expect(ks).toBeDefined();
    await ks!.set("logical/key", "v");
    expect(await ks!.get("logical/key")).toBe("v");
  });
});
