import type { RegistryAgent } from '../types/registry';

/**
 * Fetch the ASAP Lite Registry.
 * We fetch this directly from GitHub Pages or the configured raw URL.
 * In a real Next.js App Router, we use `next: { revalidate: 60 }` for ISR.
 * Normalizes registry format: endpoints.http -> endpoints.asap for UI compatibility.
 */
export async function fetchRegistry(): Promise<RegistryAgent[]> {
  // During M1 we can just fetch from a public URL or default raw content
  // Future: the real `registry.json` will be hosted via GH Pages.
  const REGISTRY_URL =
    process.env.NEXT_PUBLIC_REGISTRY_URL ||
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
    const agents = Array.isArray(data) ? data : data?.agents ?? [];
    return agents.map(normalizeRegistryAgent) as RegistryAgent[];
  } catch (error) {
    console.error('Error fetching registry:', error);
    return [];
  }
}

function normalizeRegistryAgent(agent: Record<string, unknown>): Record<string, unknown> {
    if (!agent || typeof agent !== 'object') return agent;
    const endpoints = agent.endpoints as Record<string, string> | undefined;
    if (endpoints && !endpoints.asap && endpoints.http) {
        return { ...agent, endpoints: { ...endpoints, asap: endpoints.http } };
    }
    return agent;
}

export async function fetchAgentById(id: string): Promise<RegistryAgent | null> {
  const agents = await fetchRegistry();
  return agents.find((a) => a.id === id) || null;
}
