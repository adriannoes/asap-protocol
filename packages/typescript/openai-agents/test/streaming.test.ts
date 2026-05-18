import { describe, expect, it, vi } from "vitest";

import {
  asapStreamToOpenAIAgentsRunStreamChunks,
  asapStreamToOpenAIAgentsTextStream,
} from "../src/streaming.js";

describe("asapStreamToOpenAIAgentsTextStream", () => {
  it("maps ASAP stream payloads into UTF-8 chunks", async () => {
    async function* mockSource(): AsyncIterable<{ type: string; payload: { chunk: string } }> {
      yield { type: "task_stream", payload: { chunk: "hello" } };
      yield { type: "task_stream", payload: { chunk: " world" } };
    }

    const parts: string[] = [];
    for await (const chunk of asapStreamToOpenAIAgentsTextStream(mockSource())) {
      parts.push(chunk);
    }

    expect(parts.join("")).toBe("hello world");
  });

  it("skips provider error events and continues with valid task_stream chunks", async () => {
    async function* mockSource(): AsyncIterable<unknown> {
      yield { type: "error", payload: { message: "provider failed" } };
      yield { type: "task_stream", payload: { chunk: "recovered" } };
    }

    const parts: string[] = [];
    for await (const chunk of asapStreamToOpenAIAgentsTextStream(mockSource())) {
      parts.push(chunk);
    }

    expect(parts).toEqual(["recovered"]);
  });

  it("skips malformed task_stream payloads", async () => {
    async function* mockSource(): AsyncIterable<unknown> {
      yield { type: "other" };
      yield { type: "task_stream", payload: "not-an-object" };
      yield { type: "task_stream", payload: { chunk: 1 } };
      yield { type: "task_stream", payload: {} };
    }

    const parts: string[] = [];
    for await (const chunk of asapStreamToOpenAIAgentsTextStream(mockSource())) {
      parts.push(chunk);
    }

    expect(parts).toEqual([]);
  });

  it("closes upstream iterator when consumer breaks early", async () => {
    const returned = vi.fn();
    async function* mockSource(): AsyncIterable<{ type: string; payload: { chunk: string } }> {
      try {
        yield { type: "task_stream", payload: { chunk: "a" } };
        yield { type: "task_stream", payload: { chunk: "b" } };
      } finally {
        returned();
      }
    }

    for await (const chunk of asapStreamToOpenAIAgentsTextStream(mockSource())) {
      void chunk;
      break;
    }

    expect(returned).toHaveBeenCalled();
  });
});

describe("asapStreamToOpenAIAgentsRunStreamChunks", () => {
  it("wraps chunks as text_delta objects", async () => {
    async function* mockSource(): AsyncIterable<{ type: string; payload: { chunk: string } }> {
      yield { type: "task_stream", payload: { chunk: "x" } };
    }
    const out: { type: string; text: string }[] = [];
    for await (const ev of asapStreamToOpenAIAgentsRunStreamChunks(mockSource())) {
      out.push(ev);
    }
    expect(out).toEqual([{ type: "text_delta", text: "x" }]);
  });
});
