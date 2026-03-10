/**
 * Single source of truth for Agent Builder URL (cross-platform integration).
 * Used by Header, MobileNav, Dashboard, and auth redirect.
 */
export const AGENT_BUILDER_URL =
    process.env.NEXT_PUBLIC_AGENT_BUILDER_URL ?? 'https://open-agentic-flow.vercel.app';

/** Agent Builder URL with ?from=asap query for cross-app attribution. */
export const AGENT_BUILDER_URL_WITH_FROM = `${AGENT_BUILDER_URL}?from=asap`;
