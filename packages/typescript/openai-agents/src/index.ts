/**
 * OpenAI Agents SDK (`@openai/agents`) integration: ASAP capabilities as `tool()` and related helpers.
 *
 * For static `ChatCompletionTool[]` against the Chat Completions HTTP API, use `@asap-protocol/client/adapters/openai` instead.
 */

export {
  asapToolsForOpenAIAgents,
  asapToolsForOpenAIAgentsSync,
  type AsapToolsForOpenAIAgentsOptions,
} from "./asap-to-openai-tool.js";
export {
  asapAsRemoteAgent,
  draftTaskRequestEnvelopeForRemoteAgent,
  sameProviderOrigin,
  type AsapAsRemoteAgentOptions,
  type AsapRemoteAgentMode,
  type AsapRemoteRunContext,
} from "./asap-as-remote-agent.js";
export {
  sendAsapEnvelope,
  type SendAsapEnvelopeOptions,
  type SendAsapFetch,
} from "./send-asap-envelope.js";
export { zodFromJsonSchema } from "./schema-bridge.js";
export {
  asapStreamToOpenAIAgentsRunStreamChunks,
  asapStreamToOpenAIAgentsTextStream,
  type OpenAIAgentsStreamTextDelta,
} from "./streaming.js";
export * from "./errors.js";
