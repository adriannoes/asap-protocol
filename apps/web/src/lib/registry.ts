import { Manifest } from '../types/protocol';

/**
 * Fetch the ASAP Lite Registry.
 * We fetch this directly from GitHub Pages or the configured raw URL.
 * In a real Next.js App Router, we use `next: { revalidate: 60 }` for ISR.
 */
export async function fetchRegistry(): Promise<Manifest[]> {
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
    return data as Manifest[];
  } catch (error) {
    console.error('Error fetching registry:', error);
    return [];
  }
}

export async function fetchAgentById(id: string): Promise<Manifest | null> {
  const agents = await fetchRegistry();
  return agents.find((a) => a.id === id) || null;
}
