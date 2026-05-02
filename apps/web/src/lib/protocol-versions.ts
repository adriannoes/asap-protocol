/**
 * ASAP protocol versions used for Lite Registry demos (rotation by agent index).
 * Keep in sync with PROTOCOL_VERSIONS in scripts/diversify_registry_asap_versions.py.
 */
export const PROTOCOL_VERSION_CYCLE = ['1.0.0', '1.1.0', '2.0.0', '2.1.0', '2.2.1'] as const;

export function asapVersionForFixtureIndex(index: number): string {
  const cycle = PROTOCOL_VERSION_CYCLE;
  return cycle[index % cycle.length]!;
}
