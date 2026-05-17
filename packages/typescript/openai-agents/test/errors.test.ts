import { describe, expect, it, vi } from "vitest";

import { ApprovalRequiredError, CapabilityNotGrantedError } from "../src/errors.js";

describe("adapter errors", () => {
  it("parses approval_url from non-array object detail", () => {
    const err = new ApprovalRequiredError("needs sign-off", {
      approval_url: "https://example/approve",
    });
    expect(err.detail).toEqual({ approval_url: "https://example/approve" });
  });

  it("ignores approval detail when data is not a plain object", () => {
    const err = new ApprovalRequiredError("x", []);
    expect(err.detail).toBeUndefined();
  });

  it("invokes requestCapability hook when provided", async () => {
    const hook = vi.fn().mockResolvedValue(undefined);
    const err = new CapabilityNotGrantedError("cap:read", hook, "custom");
    expect(err.message).toBe("custom");
    await err.requestCapability();
    expect(hook).toHaveBeenCalledWith("cap:read");
  });
});
