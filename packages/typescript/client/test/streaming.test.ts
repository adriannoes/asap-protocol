import { describe, expect, it, vi } from "vitest";

import { createAsapStreamClient } from "../src/streaming.js";
import type { Envelope } from "../src/types/envelope.js";
import type { EnvelopeFor } from "../src/types/envelope.js";

function sseText(...jsonLines: string[]): string {
  const parts = jsonLines.map((j) => `data: ${j}\n\n`);
  return parts.join("");
}

function taskStreamEnvelope(partial: { id: string; final: boolean; chunk?: string }): EnvelopeFor<"TaskStream"> {
  return {
    id: partial.id,
    asap_version: "2.2",
    timestamp: "2026-01-01T00:00:00.000Z",
    sender: "urn:asap:agent:provider",
    recipient: "urn:asap:agent:client",
    payload_type: "TaskStream",
    payload: {
      chunk: partial.chunk ?? "",
      progress: partial.final ? 1 : 0.25,
      final: partial.final,
      status: partial.final ? "COMPLETED" : "WORKING",
    },
  };
}

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
      input: { message: "one two" },
    },
  };
}

describe("streaming", () => {
  it("yields TaskStream envelopes from SSE until payload.final is true", async () => {
    const wire1 = JSON.stringify(taskStreamEnvelope({ id: "s1", final: false, chunk: "one " }));
    const wire2 = JSON.stringify(taskStreamEnvelope({ id: "s2", final: true, chunk: "two" }));

    const fetchMock = vi.fn(async () => {
      return new Response(sseText(wire1, wire2), {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      });
    });

    const client = createAsapStreamClient({
      baseUrl: "https://provider.example/",
      fetch: fetchMock as typeof fetch,
    });

    const chunks: EnvelopeFor<"TaskStream">[] = [];
    for await (const env of client.stream(taskRequestEnvelope())) {
      chunks.push(env);
      if (env.payload.final) {
        break;
      }
    }

    expect(chunks.length).toBeGreaterThan(0);
    expect(chunks.every((e) => e.payload_type === "TaskStream")).toBe(true);
    expect(chunks.at(-1)?.payload.final).toBe(true);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const firstCall = fetchMock.mock.calls[0];
    expect(firstCall).toBeDefined();
    const [url, init] = firstCall as unknown as [string | URL, RequestInit];
    expect(String(url)).toBe("https://provider.example/asap/stream");
    expect(init?.method).toBe("POST");
    const hdrs = init?.headers;
    if (hdrs instanceof Headers) {
      expect(hdrs.get("Accept")).toBe("text/event-stream");
      expect(hdrs.get("Content-Type")).toBe("application/json");
      expect(hdrs.get("ASAP-Version")).toBe("2.2");
    } else {
      expect(hdrs).toMatchObject({
        Accept: "text/event-stream",
        "Content-Type": "application/json",
        "ASAP-Version": "2.2",
      });
    }
    const body = typeof init?.body === "string" ? JSON.parse(init.body) : {};
    expect(body.jsonrpc).toBe("2.0");
    expect(body.method).toBe("asap.send");
    expect(body.params?.envelope?.payload_type).toBe("TaskRequest");
  });

  it("parses SSE blocks that include ignored event/id/retry lines", async () => {
    const wire = JSON.stringify(taskStreamEnvelope({ id: "s1", final: true, chunk: "done" }));
    const sse =
      `event: message\nid: abc-123\nretry: 3000\ndata: ${wire}\n\n`;
    const fetchMock = vi.fn(
      async () =>
        new Response(sse, {
          status: 200,
          headers: { "Content-Type": "text/event-stream" },
        }),
    );
    const client = createAsapStreamClient({
      baseUrl: "https://provider.example/",
      fetch: fetchMock as typeof fetch,
    });
    const chunks: EnvelopeFor<"TaskStream">[] = [];
    for await (const env of client.stream(taskRequestEnvelope())) {
      chunks.push(env);
    }
    expect(chunks).toHaveLength(1);
    expect(chunks[0]?.payload.final).toBe(true);
  });

  it("parses SSE split across multiple stream chunks", async () => {
    const wire = JSON.stringify(taskStreamEnvelope({ id: "s1", final: true, chunk: "done" }));
    const payload = `data: ${wire}\n\n`;
    const enc = new TextEncoder();
    const cut = 7;
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(enc.encode(payload.slice(0, cut)));
        controller.enqueue(enc.encode(payload.slice(cut)));
        controller.close();
      },
    });
    const fetchMock = vi.fn(
      async () =>
        new Response(stream, {
          status: 200,
          headers: { "Content-Type": "text/event-stream" },
        }),
    );
    const client = createAsapStreamClient({
      baseUrl: "https://provider.example",
      fetch: fetchMock as typeof fetch,
    });
    const chunks: EnvelopeFor<"TaskStream">[] = [];
    for await (const env of client.stream(taskRequestEnvelope())) {
      chunks.push(env);
    }
    expect(chunks).toHaveLength(1);
    expect(chunks[0]?.payload.final).toBe(true);
  });

  it("stops iteration when AbortSignal aborts (ReadableStream cancellation)", async () => {
    const wire1 = JSON.stringify(taskStreamEnvelope({ id: "s1", final: false, chunk: "x" }));

    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(new TextEncoder().encode(sseText(wire1)));
      },
    });

    const ac = new AbortController();
    const fetchMock = vi.fn(
      async () =>
        new Response(stream, {
          status: 200,
          headers: { "Content-Type": "text/event-stream" },
        }),
    );

    const client = createAsapStreamClient({
      baseUrl: "https://provider.example",
      fetch: fetchMock as typeof fetch,
    });

    await expect(async () => {
      let n = 0;
      for await (const _ of client.stream(taskRequestEnvelope(), { signal: ac.signal })) {
        n += 1;
        if (n === 1) {
          ac.abort();
        }
      }
    }).rejects.toMatchObject({ name: "AbortError" });
  });
});
