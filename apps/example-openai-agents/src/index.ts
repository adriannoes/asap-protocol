import "dotenv/config";

import { Agent, run, setDefaultOpenAIKey } from "@openai/agents";

import type { AsapExecuteClient } from "@asap-protocol/client";
import { asapToolsForOpenAIAgents } from "@asap-protocol/openai-agents";

function requiredEnv(name: string): string {
  const v = process.env[name]?.trim();
  if (!v) {
    throw new Error(`Missing ${name} — copy apps/example-openai-agents/.env.example and fill values`);
  }
  return v;
}

async function main(): Promise<void> {
  const apiKey = requiredEnv("OPENAI_API_KEY");
  const providerHref =
    process.env.ASAP_PROVIDER_URL?.trim() && process.env.ASAP_PROVIDER_URL.trim().length > 0
      ? process.env.ASAP_PROVIDER_URL.trim()
      : "http://127.0.0.1:8080/";
  const capsRaw =
    process.env.ASAP_CAPABILITIES?.trim() && process.env.ASAP_CAPABILITIES.trim().length > 0
      ? process.env.ASAP_CAPABILITIES.trim()
      : "urn:asap:cap:demo_echo";

  const capabilities = capsRaw.split(",").map((s) => s.trim()).filter(Boolean);

  const provider = new URL(providerHref);
  const client: AsapExecuteClient = {
    provider,
    capabilities,
  };

  setDefaultOpenAIKey(apiKey);

  const tools = await asapToolsForOpenAIAgents(client);
  const agent = new Agent({
    name: "example-openai-agents",
    instructions: [
      "You call ASAP capability tools to satisfy the user.",
      `Configured capabilities (comma-separated): ${capabilities.join(", ")}.`,
      "Prefer the echo capability when asked for a ping.",
    ].join(" "),
    model: "gpt-4o-mini",
    tools: [...tools],
  });

  const prompt =
    process.argv.slice(2).join(" ").trim() ||
    "Use an ASAP capability tool to echo the short phrase `hello-from-openai-agents`.";

  const result = await run(agent, prompt);
  // CLI demo output
  console.log(result.finalOutput ?? "(no text output)");
}

main().catch((err: unknown) => {
  console.error(err instanceof Error ? err.message : err);
  process.exit(1);
});
