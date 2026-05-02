/**
 * Type-safe ASAP envelopes and payloads (TS-010).
 *
 * Mirrors `src/asap/models/envelope.py` and `src/asap/models/payloads.py` wire shapes.
 */

/** Agent URN string (e.g. `urn:asap:agent:…`). */
export type AgentURN = string;

/** ISO 8601 timestamp string for wire serialization. */
export type IsoDateTimeString = string;

/**
 * Core envelope fields shared by all messages (`Envelope` in Python).
 *
 * @typeParam TPayload — Parsed payload shape when known (default `unknown`).
 */
export interface Envelope<TPayload = unknown> {
  readonly id: string;
  readonly asap_version: string;
  readonly timestamp: IsoDateTimeString;
  readonly sender: AgentURN;
  readonly recipient: AgentURN;
  readonly payload_type: string;
  readonly payload: TPayload;
  readonly correlation_id?: string | null;
  readonly trace_id?: string | null;
  readonly requires_ack?: boolean;
  readonly extensions?: Record<string, unknown> | null;
}

// --- Payloads (subset aligned with Python `payloads.py`) -------------------------------------

/** `TaskRequest.config` — extra keys allowed at runtime. */
export interface TaskRequestConfig {
  readonly timeout_seconds?: number | null;
  readonly priority?: string | null;
  readonly idempotency_key?: string | null;
  readonly streaming?: boolean | null;
  readonly persist_state?: boolean | null;
  readonly model?: string | null;
  readonly temperature?: number | null;
  readonly [key: string]: unknown;
}

export interface TaskRequestPayload {
  readonly conversation_id: string;
  readonly parent_task_id?: string | null;
  readonly skill_id: string;
  readonly input: Record<string, unknown>;
  readonly config?: TaskRequestConfig | null;
}

/** Task execution metrics (`TaskResponse.metrics`). */
export interface TaskMetricsPayload {
  readonly duration_ms?: number | null;
  readonly tokens_in?: number | null;
  readonly tokens_out?: number | null;
  readonly tokens_used?: number | null;
  readonly api_calls?: number | null;
  readonly [key: string]: unknown;
}

export interface TaskResponsePayload {
  readonly task_id: string;
  readonly status: string;
  readonly result?: Record<string, unknown> | null;
  readonly final_state?: Record<string, unknown> | null;
  readonly metrics?: TaskMetricsPayload | null;
}

export interface TaskStreamPayload {
  readonly chunk?: string;
  readonly progress?: number | null;
  readonly final: boolean;
  readonly status?: string | null;
}

export interface TaskUpdatePayload {
  readonly task_id: string;
  readonly update_type: string;
  readonly status: string;
  readonly progress?: Record<string, unknown> | null;
  readonly input_request?: Record<string, unknown> | null;
}

export interface TaskCancelPayload {
  readonly task_id: string;
  readonly reason?: string | null;
}

/** Maps ASAP `payload_type` discriminator strings to typed payloads. */
export interface PayloadTypeMap {
  readonly TaskRequest: TaskRequestPayload;
  readonly TaskResponse: TaskResponsePayload;
  readonly TaskStream: TaskStreamPayload;
  readonly TaskUpdate: TaskUpdatePayload;
  readonly TaskCancel: TaskCancelPayload;
}

/** Union of known payload type names shipped with this SDK. */
export type KnownPayloadTypeName = keyof PayloadTypeMap;

/**
 * Envelope narrowed by `payload_type` so `payload` matches the discriminator.
 *
 * @example
 * ```ts
 * const env: EnvelopeFor<"TaskStream"> = …;
 * env.payload.final; // boolean
 * ```
 */
export type EnvelopeFor<K extends KnownPayloadTypeName> = Omit<Envelope<PayloadTypeMap[K]>, "payload_type" | "payload"> & {
  readonly payload_type: K;
  readonly payload: PayloadTypeMap[K];
};

/** Any envelope whose `payload_type` is one of the known literals. */
export type KnownEnvelope = { [K in KnownPayloadTypeName]: EnvelopeFor<K> }[KnownPayloadTypeName];

/** True when `payload_type` is a key of {@link PayloadTypeMap}. */
export function isKnownPayloadType(pt: string): pt is KnownPayloadTypeName {
  return pt === "TaskRequest" ||
    pt === "TaskResponse" ||
    pt === "TaskStream" ||
    pt === "TaskUpdate" ||
    pt === "TaskCancel";
}

/**
 * Narrows a loose envelope when `payload_type` matches a known name.
 * Returns `undefined` when the discriminator is unknown or does not match `expected`.
 */
export function narrowEnvelope<K extends KnownPayloadTypeName>(
  envelope: Envelope<unknown>,
  expected: K,
): EnvelopeFor<K> | undefined {
  return envelope.payload_type === expected ? (envelope as EnvelopeFor<K>) : undefined;
}
