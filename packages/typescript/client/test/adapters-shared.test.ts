import { describe, expect, it } from "vitest";

import { jsonSchemaForCapabilityInput, jsonSchemaForCapabilityOutput } from "../src/adapters/shared.js";

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

  it("jsonSchemaForCapabilityOutput keeps typed object schemas", () => {
    expect(
      jsonSchemaForCapabilityOutput({ type: "object", properties: { ok: { type: "boolean" } } }),
    ).toEqual({
      type: "object",
      properties: { ok: { type: "boolean" } },
    });
  });

  it("jsonSchemaForCapabilityOutput falls back to open object without empty properties", () => {
    expect(jsonSchemaForCapabilityOutput(undefined)).toEqual({
      type: "object",
      additionalProperties: true,
    });
    expect(jsonSchemaForCapabilityOutput({ not: "a schema" })).toEqual({
      type: "object",
      additionalProperties: true,
    });
  });
});
