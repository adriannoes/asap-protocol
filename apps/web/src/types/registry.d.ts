/**
 * Registry-specific types for Lite Registry (registry.json).
 * RegistryEntry from Python has endpoints as { http, ws, manifest } and optional
 * repository_url, documentation_url, built_with. This type extends Manifest for
 * display on agent detail and browse pages.
 */
import type { Manifest } from './protocol';

export type RegistryAgent = Manifest & {
    /** Optional link to source code (e.g. GitHub). From Lite Registry. */
    repository_url?: string | null;
    /** Optional link to usage documentation. From Lite Registry. */
    documentation_url?: string | null;
    /** Optional framework used to build the agent (e.g. CrewAI, LangChain). From Lite Registry. */
    built_with?: string | null;
};
