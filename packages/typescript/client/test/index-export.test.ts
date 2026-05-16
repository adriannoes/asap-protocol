import { describe, expect, it } from "vitest";

import { SDK_NAME } from "../src/index.js";

describe("package entry", () => {
  it("exports SDK_NAME", () => {
    expect(SDK_NAME).toBe("@asap-protocol/client");
  });
});
