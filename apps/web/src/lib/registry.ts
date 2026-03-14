import { z } from 'zod';
import type { RegistryAgent } from '../types/registry';
import {
  RegistryResponseSchema,
  type RegistryAgentValidated,
} from './registry-schema';

const RevokedResponseSchema = z.object({
  revoked: z.array(z.object({ urn: z.string() })).default([]),
});

/**
 * ISR revalidate period (seconds) for registry data.
 * Balances with upstream cache: GitHub Pages uses max-age=600 (10 min); raw.githubusercontent.com
 * may vary. Next.js revalidates at this interval so listing visibility after a merged PR is
 * at most this long from our side; upstream cache can extend delay if using GitHub Pages.
 */
export const REGISTRY_REVALIDATE_SECONDS = process.env.REGISTRY_REVALIDATE_SECONDS
  ? Math.max(30, parseInt(process.env.REGISTRY_REVALIDATE_SECONDS, 10))
  : 60;

/**
 * Fetch the list of revoked agent URNs.
 * Returns a Set for efficient lookup.
 */
export async function fetchRevokedUrns(): Promise<Set<string>> {
  const REVOKED_URL =
    process.env.REVOKED_URL ||
    'https://raw.githubusercontent.com/adriannoes/asap-protocol/main/revoked_agents.json';

  try {
    const res = await fetch(REVOKED_URL, {
      next: { revalidate: REGISTRY_REVALIDATE_SECONDS },
    });

    if (!res.ok) {
      if (res.status === 404) return new Set();
      console.error(`Failed to fetch revoked list: ${res.statusText}`);
      return new Set();
    }

    const data = await res.json();
    const parsed = RevokedResponseSchema.safeParse(data);
    const urns = parsed.success ? parsed.data.revoked.map((e) => e.urn) : [];
    return new Set(urns);
  } catch (error) {
    console.error('Error fetching revoked list:', error);
    return new Set(); // resilient: allow listing to work when revoked list is unreachable
  }
}

/**
 * Normalizes validated registry agent to RegistryAgent (Manifest-compatible).
 * Maps endpoints.http -> endpoints.asap for UI compatibility.
 * Maps flat skills[] to capabilities.skills for Manifest shape.
 * Type assertion required: registry.json format differs from Manifest (Version, Endpoint shapes).
 */
function normalizeRegistryAgent(agent: RegistryAgentValidated): RegistryAgent {
  const endpoints = agent.endpoints ?? {};
  const asap = endpoints.asap ?? endpoints.http ?? '';
  const skills = agent.skills ?? [];
  const capabilities = {
    ...(agent.asap_version && { asap_version: agent.asap_version }),
    skills: skills.map((id) => ({ id, description: '' })),
  };
  const normalized = {
    ...agent,
    version: agent.asap_version ?? '2.0',
    endpoints: { ...endpoints, asap },
    capabilities,
  };
  return normalized as unknown as RegistryAgent;
}

/**
 * Fetch the ASAP Lite Registry.
 * We fetch from REGISTRY_URL (GitHub Pages or raw URL). Next.js ISR uses REGISTRY_REVALIDATE_SECONDS.
 * Normalizes registry format: endpoints.http -> endpoints.asap for UI compatibility.
 * Validates response with Zod.
 */
export async function fetchRegistry(): Promise<RegistryAgent[]> {
  // Server-side only: use REGISTRY_URL (not NEXT_PUBLIC_) to avoid leaking in client bundle.
  const REGISTRY_URL =
    process.env.REGISTRY_URL ||
    'https://raw.githubusercontent.com/adriannoes/asap-protocol/main/registry.json';

  try {
    const res = await fetch(REGISTRY_URL, {
      next: { revalidate: REGISTRY_REVALIDATE_SECONDS },
    });

    if (!res.ok) {
      if (res.status === 404) {
        // Return empty if registry not founded yet
        return [];
      }
      throw new Error(`Failed to fetch registry: ${res.statusText}`);
    }

    const data = await res.json();
    const parsed = RegistryResponseSchema.safeParse(data);
    if (!parsed.success) {
      console.error('Registry schema validation failed:', parsed.error.flatten());
      return [];
    }
    const rawAgents = Array.isArray(parsed.data) ? parsed.data : parsed.data.agents;
    return rawAgents.map((a) => normalizeRegistryAgent(a));
  } catch (error) {
    console.error('Error fetching registry:', error);
    return [];
  }
}

export async function fetchAgentById(id: string): Promise<RegistryAgent | null> {
  const agents = await fetchRegistry();
  return agents.find((a) => a.id === id) || null;
}
