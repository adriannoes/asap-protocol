import { describe, expect, it } from "vitest";

import { asapToolsForAnthropic } from "../src/adapters/anthropic.js";

describe("adapters / Anthropic Messages tools", () => {
  it("produces tool definitions with name, description, and input_schema", () => {
    const tools = asapToolsForAnthropic(
      { capabilities: ["urn:asap:cap:weather"] },
      {
        descriptions: { "urn:asap:cap:weather": "Weather lookup" },
        inputSchemas: {
          "urn:asap:cap:weather": {
            type: "object",
            properties: { city: { type: "string" } },
            required: ["city"],
            additionalProperties: false,
          },
        },
      },
    );

    expect(tools).toHaveLength(1);
    expect(tools[0]).toEqual({
      name: "weather",
      description: "Weather lookup",
      input_schema: {
        type: "object",
        properties: { city: { type: "string" } },
        required: ["city"],
        additionalProperties: false,
      },
    });
  });
});
