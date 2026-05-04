import { expectAssignable, expectNotAssignable, expectType } from "tsd";

import type {
  Envelope,
  EnvelopeFor,
  KnownEnvelope,
  PayloadTypeMap,
  TaskRequestPayload,
  TaskStreamPayload,
} from "../src/types/envelope.js";

// Envelope<T> carries payload
declare const taskReq: Envelope<TaskRequestPayload>;
expectType<TaskRequestPayload>(taskReq.payload);

// Discriminated narrowing
declare const streamEnv: EnvelopeFor<"TaskStream">;
expectType<TaskStreamPayload>(streamEnv.payload);
expectType<boolean>(streamEnv.payload.final);
expectType<"TaskStream">(streamEnv.payload_type);

// Known envelope union accepts each variant
expectAssignable<KnownEnvelope>(streamEnv);

// Wrong payload shape must not assign to EnvelopeFor
expectNotAssignable<EnvelopeFor<"TaskRequest">>(streamEnv);

// Payload map lookup
expectType<TaskRequestPayload>({} as PayloadTypeMap["TaskRequest"]);
