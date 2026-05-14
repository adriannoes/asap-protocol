import { describe, expect, it } from "vitest";

import { jsonSchemaForCapabilityInput } from "../src/adapters/shared.js";

describe("adapter shared helpers", () => {
  it("jsonSchemaForCapabilityInput falls back to permissive object schema", () => {
    expect(jsonSchemaForCapabilityInput(undefined)).toMatchObject({
      type: "object",
      additionalProperties: true,
    });
    expect(jsonSchemaForCapabilityInput({ not: "a schema" })).toMatchObject({
      type: "object",
      additionalProperties: true,
    });
    expect(jsonSchemaForCapabilityInput({ type: "object", properties: {} })).toEqual({
      type: "object",
      properties: {},
    });
  });
});
