import { describe, expect, it, vi } from "vitest";

import { createAsapStreamClient, streamTaskStreamEnvelopes } from "../src/streaming.js";
import type { Envelope } from "../src/types/envelope.js";

function taskRequestEnvelope(): Envelope<unknown> {
  return {
    id: "env-req-1",
    asap_version: "2.2",
    timestamp: "2026-01-01T00:00:00.000Z",
    sender: "urn:asap:agent:client",
    recipient: "urn:asap:agent:provider",
    payload_type: "TaskRequest",
    payload: {
      conversation_id: "conv-1",
      skill_id: "echo",
      input: { message: "x" },
    },
  };
}

describe("streaming error paths", () => {
  it("throws on non-OK HTTP response", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("oops", { status: 503 }));
    const client = createAsapStreamClient({
      baseUrl: "https://provider.example",
      fetch: fetchMock as typeof fetch,
    });

    await expect(async () => {
      for await (const _ of client.stream(taskRequestEnvelope())) {
        /* drain */
      }
    }).rejects.toThrow(/HTTP 503/u);
  });

  it("throws when SSE data is not valid JSON", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response("data: not-json\n\n", {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      }),
    );
    const client = createAsapStreamClient({
      baseUrl: "https://provider.example",
      fetch: fetchMock as typeof fetch,
    });

    await expect(async () => {
      for await (const _ of client.stream(taskRequestEnvelope())) {
        /* drain */
      }
    }).rejects.toThrow(/invalid JSON/u);
  });

  it("throws when envelope is not TaskStream", async () => {
    const bad = JSON.stringify({
      id: "x",
      asap_version: "2.2",
      timestamp: "2026-01-01T00:00:00.000Z",
      sender: "a",
      recipient: "b",
      payload_type: "TaskResponse",
      payload: {},
    });
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(`data: ${bad}\n\n`, {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      }),
    );
    const client = createAsapStreamClient({
      baseUrl: "https://provider.example",
      fetch: fetchMock as typeof fetch,
    });

    await expect(async () => {
      for await (const _ of client.stream(taskRequestEnvelope())) {
        /* drain */
      }
    }).rejects.toThrow(/expected TaskStream/u);
  });

  it("streamTaskStreamEnvelopes throws when TaskStream payload.final is missing", async () => {
    const bad = JSON.stringify({
      id: "x",
      asap_version: "2.2",
      timestamp: "2026-01-01T00:00:00.000Z",
      sender: "a",
      recipient: "b",
      payload_type: "TaskStream",
      payload: { chunk: "", progress: 0, status: "WORKING" },
    });
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(`data: ${bad}\n\n`, {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      }),
    );

    await expect(async () => {
      for await (const _ of streamTaskStreamEnvelopes({
        streamUrl: "https://provider.example/asap/stream",
        envelope: taskRequestEnvelope(),
        fetch: fetchMock as typeof fetch,
      })) {
        /* drain */
      }
    }).rejects.toThrow(/missing boolean final/u);
  });
});
