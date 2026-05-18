/**
 * Bridge ASAP TaskStream-style payloads into UTF-8 text chunks suitable for OpenAI Agents streaming UX.
 *
 * Pair with `@asap-protocol/client` streaming helpers (`createAsapStreamClient`, `streamTaskStreamEnvelopes`).
 */

function isRecord(x: unknown): x is Record<string, unknown> {
  return typeof x === "object" && x !== null && !Array.isArray(x);
}

/** Streaming text delta aligned with incremental assistant output (surface-only shape). */
export interface OpenAIAgentsStreamTextDelta {
  readonly type: "text_delta";
  readonly text: string;
}

export async function* asapStreamToOpenAIAgentsTextStream(source: AsyncIterable<unknown>): AsyncIterable<string> {
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

/**
 * Same mapping as {@link asapStreamToOpenAIAgentsTextStream}, wrapped as `{ type: "text_delta" }` chunks.
 */
export async function* asapStreamToOpenAIAgentsRunStreamChunks(
  source: AsyncIterable<unknown>,
): AsyncIterable<OpenAIAgentsStreamTextDelta> {
  for await (const text of asapStreamToOpenAIAgentsTextStream(source)) {
    yield { type: "text_delta", text };
  }
}
