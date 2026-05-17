import { describe, expect, it } from "vitest";

import { zodFromJsonSchema } from "../src/schema-bridge.js";

describe("zodFromJsonSchema", () => {
  it("maps $ref to a permissive object schema", () => {
    const s = zodFromJsonSchema({ $ref: "#/definitions/Foo" });
    expect(s.safeParse({ a: 1 }).success).toBe(true);
  });

  it("maps oneOf to a Zod union", () => {
    const s = zodFromJsonSchema({
      oneOf: [{ type: "string" }, { type: "number" }],
    });
    expect(s.safeParse("x").success).toBe(true);
    expect(s.safeParse(3).success).toBe(true);
    expect(s.safeParse({}).success).toBe(false);
  });

  it("unwraps a single oneOf branch", () => {
    const s = zodFromJsonSchema({ oneOf: [{ type: "string" }] });
    expect(s.safeParse("one").success).toBe(true);
  });

  it("treats empty oneOf as unknown", () => {
    const s = zodFromJsonSchema({ oneOf: [] });
    expect(s.safeParse({ x: 1 }).success).toBe(true);
  });

  it("maps object properties with required keys", () => {
    const s = zodFromJsonSchema({
      type: "object",
      properties: { message: { type: "string" } },
      required: ["message"],
    });
    expect(s.safeParse({ message: "hi" }).success).toBe(true);
    expect(s.safeParse({}).success).toBe(false);
  });

  it("maps integer, boolean, and array schemas", () => {
    expect(zodFromJsonSchema({ type: "integer" }).safeParse(7).success).toBe(true);
    expect(zodFromJsonSchema({ type: "boolean" }).safeParse(false).success).toBe(true);
    expect(zodFromJsonSchema({ type: "array" }).safeParse([1, 2]).success).toBe(true);
  });

  it("falls back for schemas without a recognized type", () => {
    const s = zodFromJsonSchema({ description: "no explicit type" });
    expect(s.safeParse({ k: "v" }).success).toBe(true);
  });

  it("falls back to open record when object has empty properties", () => {
    const s = zodFromJsonSchema({ type: "object", properties: {} });
    expect(s.safeParse({ any: "thing" }).success).toBe(true);
  });
});
