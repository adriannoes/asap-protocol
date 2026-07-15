import type { JSX } from 'react';

/**
 * Screen-reader notice for `target="_blank"` links (Lab II external docs).
 *
 * @example
 * <a href={url} target="_blank" rel="noopener noreferrer">
 *   Docs <OpensInNewTabHint />
 * </a>
 */
export function OpensInNewTabHint(): JSX.Element {
  return <span className="sr-only">(opens in a new tab)</span>;
}

/** Keyboard focus ring for external Lab II links (aligned with agent-card / Hero). */
export const EXTERNAL_LINK_FOCUS_CLASS =
  'outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/50 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-950';
