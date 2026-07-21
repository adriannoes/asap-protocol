import { describe, expect, it } from "vitest";

import { asapToolsForOpenAI } from "../src/adapters/openai.js";

describe("adapters / OpenAI Chat Completions tools", () => {
  it("produces ChatCompletion-style tools with function names and JSON Schema parameters", () => {
    const tools = asapToolsForOpenAI(
      { capabilities: ["urn:asap:cap:echo"] },
      {
        descriptions: { "urn:asap:cap:echo": "Echo input" },
        inputSchemas: {
          "urn:asap:cap:echo": {
            type: "object",
            properties: { message: { type: "string" } },
            required: ["message"],
            additionalProperties: false,
          },
        },
      },
    );

    expect(tools).toHaveLength(1);
    expect(tools[0]).toEqual({
      type: "function",
      function: {
        name: "echo",
        description: "Echo input",
        parameters: {
          type: "object",
          properties: { message: { type: "string" } },
          required: ["message"],
          additionalProperties: false,
        },
      },
    });
  });
});
