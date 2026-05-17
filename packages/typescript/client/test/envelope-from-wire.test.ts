import { describe, expect, it } from "vitest";

import { envelopeFromWireJson } from "../src/streaming.js";

describe("envelopeFromWireJson", () => {
  it("rejects non-object wire JSON", () => {
    expect(() => envelopeFromWireJson(null)).toThrow(/must be an object/u);
  });

  it("normalizes non-string timestamp to empty string", () => {
    const env = envelopeFromWireJson({
      id: "e1",
      asap_version: "2.2",
      timestamp: 99,
      sender: "a",
      recipient: "b",
      payload_type: "TaskStream",
      payload: { final: true },
    });
    expect(env.timestamp).toBe("");
  });

  it("maps extensions null and omits invalid extension shapes", () => {
    const withNull = envelopeFromWireJson({
      id: "e1",
      asap_version: "2.2",
      timestamp: "2026-01-01T00:00:00.000Z",
      sender: "a",
      recipient: "b",
      payload_type: "x",
      payload: {},
      extensions: null,
    });
    expect(withNull.extensions).toBeNull();

    const withNumber = envelopeFromWireJson({
      id: "e2",
      asap_version: "2.2",
      timestamp: "2026-01-01T00:00:00.000Z",
      sender: "a",
      recipient: "b",
      payload_type: "x",
      payload: {},
      extensions: 42,
    });
    expect(withNumber.extensions).toBeUndefined();
  });
});
