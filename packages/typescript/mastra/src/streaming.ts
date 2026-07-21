/**
 * Bridge ASAP streaming payloads into Mastra-compatible text chunks.
 *
 * Async generator iteration propagates consumer backpressure: the upstream `source` iterator
 * only advances after each `yield`, so a slow consumer naturally throttles reads.
 *
 */

function isRecord(x: unknown): x is Record<string, unknown> {
  return typeof x === "object" && x !== null && !Array.isArray(x);
}

export async function* asapStreamToMastraTextStream(source: AsyncIterable<unknown>): AsyncIterable<string> {
  const it = source[Symbol.asyncIterator]();
  try {
    while (true) {
      const { value: event, done } = await it.next();
      if (done) {
        return;
      }
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
  } finally {
    await it.return?.();
  }
}
