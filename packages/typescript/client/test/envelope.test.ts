import { describe, expect, it } from "vitest";

import {
  isKnownPayloadType,
  narrowEnvelope,
  type Envelope,
  type EnvelopeFor,
} from "../src/types/envelope.js";

describe("envelope (runtime)", () => {
  it("isKnownPayloadType recognizes built-in names", () => {
    expect(isKnownPayloadType("TaskStream")).toBe(true);
    expect(isKnownPayloadType("Unknown")).toBe(false);
  });

  it("narrowEnvelope refines by payload_type", () => {
    const loose: Envelope<unknown> = {
      id: "1",
      asap_version: "2.2",
      timestamp: "2026-01-01T00:00:00Z",
      sender: "urn:asap:agent:a",
      recipient: "urn:asap:agent:b",
      payload_type: "TaskStream",
      payload: { final: true, chunk: "hi" },
    };
    const t = narrowEnvelope(loose, "TaskStream");
    expect(t).toBeDefined();
    expect(t!.payload.final).toBe(true);
    expect(narrowEnvelope(loose, "TaskRequest")).toBeUndefined();
  });

  it("EnvelopeFor has correlated payload", () => {
    const e: EnvelopeFor<"TaskRequest"> = {
      id: "1",
      asap_version: "2.2",
      timestamp: "2026-01-01T00:00:00Z",
      sender: "urn:asap:agent:a",
      recipient: "urn:asap:agent:b",
      payload_type: "TaskRequest",
      payload: {
        conversation_id: "c1",
        skill_id: "echo",
        input: {},
      },
    };
    expect(e.payload.skill_id).toBe("echo");
  });
});
