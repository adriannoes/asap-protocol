/**
 * Lite Registry and well-known manifest discovery.
 *
 * @see `src/asap/discovery/registry.py`, `src/asap/discovery/wellknown.py`
 */

import { isRecord } from "./internal/type-guards.js";

/** Standard ASAP manifest path (RFC 8615). */
export const WELLKNOWN_MANIFEST_PATH = "/.well-known/asap/manifest.json" as const;

/** Official GitHub Pages Lite Registry (SD-11). */
export const DEFAULT_REGISTRY_URL = "https://asap-protocol.github.io/registry/registry.json" as const;

export type DiscoveryFetch = typeof fetch;

export interface ListProvidersOptions {
  readonly fetch?: DiscoveryFetch;
  readonly signal?: AbortSignal;
}

export interface SearchProvidersOptions {
  readonly registryUrl?: string;
  /** When set, skips fetching and searches this snapshot (tests / callers with cached data). */
  readonly registry?: LiteRegistry;
  readonly fetch?: DiscoveryFetch;
  readonly signal?: AbortSignal;
}

export interface DiscoverProviderOptions {
  readonly fetch?: DiscoveryFetch;
  readonly signal?: AbortSignal;
}

export interface RegistryEntry {
  readonly id: string;
  readonly name: string;
  readonly description: string;
  readonly endpoints: Record<string, string>;
  readonly skills: string[];
  readonly category?: string | null;
  readonly tags: string[];
  readonly asap_version: string;
  readonly repository_url?: string | null;
  readonly documentation_url?: string | null;
  readonly built_with?: string | null;
  readonly verification?: { readonly status: string; readonly verified_at?: string | null } | null;
  readonly online_check?: boolean | null;
  /** Derived from manifest `capabilities.hardware.class` (v2.4+). */
  readonly hardware_class?: string | null;
  /** Derived from manifest `capabilities.inference.modes` (v2.4+). */
  readonly inference_modes: string[];
  /** Derived from manifest `capabilities.hardware.io` (v2.4+). */
  readonly hardware_io: string[];
}

export interface LiteRegistry {
  readonly version: string;
  readonly updated_at: string;
  readonly agents: RegistryEntry[];
}

export interface AsapSkill {
  readonly id: string;
  readonly description: string;
  readonly input_schema?: unknown;
  readonly output_schema?: unknown;
}

export interface AsapCapabilityBlock {
  readonly asap_version: string;
  readonly skills: AsapSkill[];
  readonly state_persistence?: boolean;
  readonly streaming?: boolean;
  readonly mcp_tools?: string[];
}

export interface AsapManifest {
  readonly id: string;
  readonly name: string;
  readonly version: string;
  readonly description: string;
  readonly capabilities: AsapCapabilityBlock;
  readonly endpoints: { readonly asap: string; readonly events?: string | null };
  readonly supported_versions?: string[];
  readonly auth?: unknown;
  readonly signature?: string | null;
  readonly sla?: unknown;
  readonly verification?: unknown;
  readonly ttl_seconds?: number;
}

function parseStringListField(raw: unknown, field: string, index: number): string[] {
  if (raw === undefined) {
    return [];
  }
  if (!Array.isArray(raw)) {
    throw new Error(`registry.agents[${index}]: ${field} must be an array`);
  }
  return raw.map((item, j) => {
    if (typeof item !== "string") {
      throw new Error(`registry.agents[${index}]: ${field}[${j}] must be a string`);
    }
    return item;
  });
}

function parseRegistryEntry(raw: unknown, index: number): RegistryEntry {
  if (!isRecord(raw)) {
    throw new Error(`registry.agents[${index}]: expected object`);
  }
  const id = raw.id;
  const name = raw.name;
  const description = raw.description;
  const endpoints = raw.endpoints;
  const skills = raw.skills;
  const asap_version = raw.asap_version;
  if (typeof id !== "string") throw new Error(`registry.agents[${index}]: missing id`);
  if (typeof name !== "string") throw new Error(`registry.agents[${index}]: missing name`);
  if (typeof description !== "string") throw new Error(`registry.agents[${index}]: missing description`);
  if (!isRecord(endpoints)) throw new Error(`registry.agents[${index}]: endpoints must be an object`);
  for (const [k, v] of Object.entries(endpoints)) {
    if (typeof v !== "string") {
      throw new Error(`registry.agents[${index}]: endpoints.${k} must be a string`);
    }
  }
  if (!Array.isArray(skills)) throw new Error(`registry.agents[${index}]: skills must be an array`);
  for (let j = 0; j < skills.length; j += 1) {
    if (typeof skills[j] !== "string") {
      throw new Error(`registry.agents[${index}]: skills[${j}] must be a string`);
    }
  }
  if (typeof asap_version !== "string") throw new Error(`registry.agents[${index}]: missing asap_version`);
  const tags = raw.tags;
  let tagList: string[] = [];
  if (tags !== undefined) {
    if (!Array.isArray(tags)) {
      throw new Error(`registry.agents[${index}]: tags must be an array`);
    }
    tagList = tags.map((t, j) => {
      if (typeof t !== "string") throw new Error(`registry.agents[${index}]: tags[${j}] must be a string`);
      return t;
    });
  }

  return {
    id,
    name,
    description,
    endpoints: endpoints as Record<string, string>,
    skills,
    category: typeof raw.category === "string" || raw.category === null ? raw.category : undefined,
    tags: tagList,
    asap_version,
    repository_url:
      typeof raw.repository_url === "string" || raw.repository_url === null ? raw.repository_url : undefined,
    documentation_url:
      typeof raw.documentation_url === "string" || raw.documentation_url === null
        ? raw.documentation_url
        : undefined,
    built_with: typeof raw.built_with === "string" || raw.built_with === null ? raw.built_with : undefined,
    verification: raw.verification as RegistryEntry["verification"],
    online_check: typeof raw.online_check === "boolean" || raw.online_check === null ? raw.online_check : undefined,
    hardware_class:
      typeof raw.hardware_class === "string" || raw.hardware_class === null ? raw.hardware_class : undefined,
    inference_modes: parseStringListField(raw.inference_modes, "inference_modes", index),
    hardware_io: parseStringListField(raw.hardware_io, "hardware_io", index),
  };
}

function parseLiteRegistry(data: unknown): LiteRegistry {
  if (!isRecord(data)) throw new Error("registry: expected a JSON object");
  const version = data.version;
  const updated_at = data.updated_at;
  const agents = data.agents;
  if (typeof version !== "string") throw new Error("registry: missing version");
  if (typeof updated_at !== "string") throw new Error("registry: missing updated_at");
  if (!Array.isArray(agents)) throw new Error("registry: agents must be an array");
  return {
    version,
    updated_at,
    agents: agents.map((a, i) => parseRegistryEntry(a, i)),
  };
}

function parseSkill(raw: unknown, path: string): AsapSkill {
  if (!isRecord(raw)) throw new Error(`${path}: expected object`);
  const id = raw.id;
  const description = raw.description;
  if (typeof id !== "string") throw new Error(`${path}: skill missing id`);
  if (typeof description !== "string") throw new Error(`${path}: skill missing description`);
  return {
    id,
    description,
    input_schema: raw.input_schema,
    output_schema: raw.output_schema,
  };
}

function parseAsapManifest(data: unknown): AsapManifest {
  if (!isRecord(data)) throw new Error("manifest: expected a JSON object");
  const id = data.id;
  const name = data.name;
  const version = data.version;
  const description = data.description;
  const capabilities = data.capabilities;
  const endpoints = data.endpoints;
  if (typeof id !== "string") throw new Error("manifest: missing id");
  if (typeof name !== "string") throw new Error("manifest: missing name");
  if (typeof version !== "string") throw new Error("manifest: missing version");
  if (typeof description !== "string") throw new Error("manifest: missing description");
  if (!isRecord(capabilities)) throw new Error("manifest: capabilities must be an object");
  const asap_version = capabilities.asap_version;
  const skillsRaw = capabilities.skills;
  if (typeof asap_version !== "string") throw new Error("manifest: capabilities.asap_version must be a string");
  if (!Array.isArray(skillsRaw)) throw new Error("manifest: capabilities.skills must be an array");
  const skills = skillsRaw.map((s, i) => parseSkill(s, `manifest.capabilities.skills[${i}]`));
  if (!isRecord(endpoints)) throw new Error("manifest: endpoints must be an object");
  const asap = endpoints.asap;
  if (typeof asap !== "string") throw new Error("manifest: endpoints.asap must be a string");
  const events = endpoints.events;
  if (events !== undefined && events !== null && typeof events !== "string") {
    throw new Error("manifest: endpoints.events must be a string or null");
  }

  return {
    id,
    name,
    version,
    description,
    capabilities: {
      asap_version,
      skills,
      state_persistence: typeof capabilities.state_persistence === "boolean" ? capabilities.state_persistence : undefined,
      streaming: typeof capabilities.streaming === "boolean" ? capabilities.streaming : undefined,
      mcp_tools: Array.isArray(capabilities.mcp_tools)
        ? capabilities.mcp_tools.filter((t): t is string => typeof t === "string")
        : undefined,
    },
    endpoints: { asap, events: events === undefined ? undefined : events },
    supported_versions: Array.isArray(data.supported_versions)
      ? data.supported_versions.filter((v): v is string => typeof v === "string")
      : undefined,
    auth: data.auth,
    signature: typeof data.signature === "string" || data.signature === null ? data.signature : undefined,
    sla: data.sla,
    verification: data.verification,
    ttl_seconds: typeof data.ttl_seconds === "number" ? data.ttl_seconds : undefined,
  };
}

/** Join base URL with the well-known manifest path (matches Python `rstrip('/') + path`). */
export function manifestUrlForBase(baseUrl: string): string {
  const trimmed = baseUrl.replace(/\/+$/u, "");
  return `${trimmed}${WELLKNOWN_MANIFEST_PATH}`;
}

/**
 * Fetch and parse the Lite Registry JSON (`registry.json`).
 *
 * @param registry URL of `registry.json` (e.g. {@link DEFAULT_REGISTRY_URL})
 */
export async function listProviders(registry: string, options?: ListProvidersOptions): Promise<LiteRegistry> {
  const doFetch = options?.fetch ?? globalThis.fetch;
  const response = await doFetch(registry, {
    signal: options?.signal,
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`registry request failed: HTTP ${String(response.status)} ${registry}`);
  }
  let body: unknown;
  try {
    body = await response.json();
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    throw new Error(`registry: invalid JSON (${msg})`);
  }
  return parseLiteRegistry(body);
}

function entryMatchesIntent(entry: RegistryEntry, needle: string): boolean {
  if (entry.id.toLowerCase().includes(needle)) return true;
  if (entry.name.toLowerCase().includes(needle)) return true;
  if (entry.description.toLowerCase().includes(needle)) return true;
  const cat = entry.category;
  if (typeof cat === "string" && cat.toLowerCase().includes(needle)) return true;
  for (const s of entry.skills) {
    if (s.toLowerCase().includes(needle)) return true;
  }
  for (const t of entry.tags) {
    if (t.toLowerCase().includes(needle)) return true;
  }
  return false;
}

/**
 * Search registry agents by intent string (case-insensitive match on id, name, description,
 * category, skills, and tags). When `registry` is omitted, fetches {@link DEFAULT_REGISTRY_URL}
 * unless `registryUrl` overrides it.
 */
export async function searchProviders(intent: string, options?: SearchProvidersOptions): Promise<RegistryEntry[]> {
  const needle = intent.trim().toLowerCase();
  if (needle.length === 0) {
    return [];
  }
  const snapshot =
    options?.registry ??
    (await listProviders(options?.registryUrl ?? DEFAULT_REGISTRY_URL, {
      fetch: options?.fetch,
      signal: options?.signal,
    }));
  return snapshot.agents.filter((a) => entryMatchesIntent(a, needle));
}

/**
 * Discover an agent manifest from a base URL via `GET /.well-known/asap/manifest.json`.
 */
export async function discoverProvider(baseUrl: string, options?: DiscoverProviderOptions): Promise<AsapManifest> {
  const manifestUrl = manifestUrlForBase(baseUrl);
  const doFetch = options?.fetch ?? globalThis.fetch;
  const response = await doFetch(manifestUrl, {
    signal: options?.signal,
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`manifest request failed: HTTP ${String(response.status)} ${manifestUrl}`);
  }
  let body: unknown;
  try {
    body = await response.json();
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    throw new Error(`manifest: invalid JSON (${msg})`);
  }
  return parseAsapManifest(body);
}
