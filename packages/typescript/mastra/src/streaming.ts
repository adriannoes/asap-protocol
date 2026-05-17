/**
 * Bridge ASAP streaming payloads into Mastra-compatible text chunks.
 *
 * Async generator iteration propagates consumer backpressure: the upstream `source` iterator
 * only advances after each `yield`, so a slow consumer naturally throttles reads.
 *
 * @see sprint task 4.1 for SSE parsing and backpressure.
 */

function isRecord(x: unknown): x is Record<string, unknown> {
  return typeof x === "object" && x !== null && !Array.isArray(x);
}

export async function* asapStreamToMastraTextStream(source: AsyncIterable<unknown>): AsyncIterable<string> {
  for await (const event of source) {
    if (!isRecord(event) || event.type !== "task_stream") {
      continue;
    }
    const payload = event.payload;
    if (!isRecord(payload)) {
      continue;
    }
    const chunk = payload.chunk;
    if (typeof chunk === "string") {
      yield chunk;
    }
  }
}
