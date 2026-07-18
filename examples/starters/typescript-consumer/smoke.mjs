#!/usr/bin/env node
/**
 * Thin TypeScript consumer smoke (DIST-003 / D2 / D3).
 *
 * Offline by default: createHost + createAgent with MemoryStorage.
 * Optional live path: set ASAP_PROVIDER_URL to discover + list capabilities.
 *
 * Non-loopback URLs must use HTTPS (TLS). No API keys required for the default path.
 */
import {
  createHost,
  createAgent,
  MemoryStorage,
  discoverProvider,
  listCapabilities,
} from "@asap-protocol/client";

/**
 * Require https: for remote hosts; allow http: only for loopback.
 *
 * @param {string} urlString
 * @param {string} label
 * @returns {URL}
 */
function assertHttpsOrLoopback(urlString, label) {
  let url;
  try {
    url = new URL(urlString);
  } catch {
    throw new Error(
      `${label} must be an absolute http(s) URL, got: ${JSON.stringify(urlString)}`,
    );
  }

  if (url.protocol !== "http:" && url.protocol !== "https:") {
    throw new Error(
      `${label} must use http: or https:, got protocol ${JSON.stringify(url.protocol)} for ${JSON.stringify(urlString)}`,
    );
  }

  if (url.protocol === "https:") {
    return url;
  }

  const host = url.hostname.toLowerCase();
  const isLoopback =
    host === "127.0.0.1" || host === "localhost" || host === "::1";
  if (!isLoopback) {
    throw new Error(
      `${label} must use HTTPS for non-loopback hosts; got ${JSON.stringify(urlString)} (host=${host}). Loopback http://127.0.0.1 / localhost / ::1 is allowed.`,
    );
  }
  return url;
}

async function runOfflineIdentity() {
  const storage = new MemoryStorage();
  const host = await createHost({ storage });
  const agent = await createAgent(host, { mode: "delegated" });
  return { host, agent };
}

async function runOptionalLive(agent) {
  const raw = process.env.ASAP_PROVIDER_URL?.trim();
  if (raw === undefined || raw.length === 0) {
    return null;
  }

  assertHttpsOrLoopback(raw, "ASAP_PROVIDER_URL");

  const manifest = await discoverProvider(raw);
  const asapEndpoint = manifest.endpoints?.asap;
  if (typeof asapEndpoint !== "string" || asapEndpoint.length === 0) {
    throw new Error(
      `manifest.endpoints.asap must be a non-empty string URL, got: ${JSON.stringify(asapEndpoint)}`,
    );
  }
  const provider = assertHttpsOrLoopback(
    asapEndpoint,
    "manifest.endpoints.asap",
  );
  const agentJwt = await agent.signAgentJwt({ aud: provider.origin });
  const listed = await listCapabilities(provider, { agentJwt });
  return {
    providerId: manifest.id,
    providerName: manifest.name,
    capabilityCount: listed.capabilities.length,
  };
}

async function main() {
  const { host, agent } = await runOfflineIdentity();
  console.log(
    `identity ok: host=${host.hostId} agent=${agent.agentId} mode=${agent.mode}`,
  );

  const live = await runOptionalLive(agent);
  if (live !== null) {
    console.log(
      `live ok: provider=${live.providerId} (${live.providerName}) capabilities=${live.capabilityCount}`,
    );
  } else {
    console.log("live skipped: ASAP_PROVIDER_URL unset (offline smoke)");
  }

  console.log("typescript-consumer smoke: PASS");
}

main().catch((err) => {
  const msg = err instanceof Error ? err.message : String(err);
  console.error(`typescript-consumer smoke: FAIL — ${msg}`);
  process.exit(1);
});
