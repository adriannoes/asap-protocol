import { describe, expect, it } from "vitest";

import { asapStreamToMastraTextStream } from "../src/streaming.js";

describe("asapStreamToMastraTextStream", () => {
  it("maps ASAP stream payloads into Mastra text chunks", async () => {
    async function* mockSource(): AsyncIterable<{ type: string; payload: { chunk: string } }> {
      yield { type: "task_stream", payload: { chunk: "hello" } };
      yield { type: "task_stream", payload: { chunk: " world" } };
    }

    const parts: string[] = [];
    for await (const chunk of asapStreamToMastraTextStream(mockSource())) {
      parts.push(chunk);
    }

    expect(parts.join("")).toBe("hello world");
  });

  it("skips events without string task_stream chunks", async () => {
    async function* mockSource(): AsyncIterable<unknown> {
      yield { type: "other" };
      yield { type: "task_stream", payload: "not-an-object" };
      yield { type: "task_stream", payload: { chunk: 1 } };
      yield { type: "task_stream", payload: {} };
    }

    const parts: string[] = [];
    for await (const chunk of asapStreamToMastraTextStream(mockSource())) {
      parts.push(chunk);
    }

    expect(parts).toEqual([]);
  });

  it("propagates backpressure from a slow consumer", async () => {
    let pulled = 0;
    async function* mockSource(): AsyncIterable<{ type: string; payload: { chunk: string } }> {
      pulled += 1;
      yield { type: "task_stream", payload: { chunk: "a" } };
      pulled += 1;
      yield { type: "task_stream", payload: { chunk: "b" } };
    }

    const gen = asapStreamToMastraTextStream(mockSource());
    const it = gen[Symbol.asyncIterator]();
    const first = await it.next();
    expect(first.value).toBe("a");
    expect(pulled).toBe(1);

    const second = await it.next();
    expect(second.value).toBe("b");
    expect(pulled).toBe(2);
  });
});
