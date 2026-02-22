import type { RegistryAgent } from '../types/registry';
import { RegistryResponseSchema } from './registry-schema';

/**
 * Fetch the ASAP Lite Registry.
 * We fetch this directly from GitHub Pages or the configured raw URL.
 * In a real Next.js App Router, we use `next: { revalidate: 60 }` for ISR.
 * Normalizes registry format: endpoints.http -> endpoints.asap for UI compatibility.
 * Validates response with Zod (IMP-4).
 */
export async function fetchRegistry(): Promise<RegistryAgent[]> {
  // During M1 we can just fetch from a public URL or default raw content
  // Future: the real `registry.json` will be hosted via GH Pages.
  // Server-side only: use REGISTRY_URL (not NEXT_PUBLIC_) to avoid leaking in client bundle.
  const REGISTRY_URL =
    process.env.REGISTRY_URL ||
    'https://raw.githubusercontent.com/adriannoes/asap-protocol/main/registry.json';

  try {
    const res = await fetch(REGISTRY_URL, {
      next: { revalidate: 60 }, // ISR every minute
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
    return rawAgents.map((a) =>
        normalizeRegistryAgent(a as { endpoints: Record<string, string>; [k: string]: unknown })
    );
  } catch (error) {
    console.error('Error fetching registry:', error);
    return [];
  }
}

function normalizeRegistryAgent(agent: {
    endpoints: Record<string, string>;
    [k: string]: unknown;
}): RegistryAgent {
    const endpoints = agent.endpoints ?? {};
    if (!endpoints.asap && endpoints.http) {
        return { ...agent, endpoints: { ...endpoints, asap: endpoints.http } } as unknown as RegistryAgent;
    }
    return agent as unknown as RegistryAgent;
}

export async function fetchAgentById(id: string): Promise<RegistryAgent | null> {
  const agents = await fetchRegistry();
  return agents.find((a) => a.id === id) || null;
}
