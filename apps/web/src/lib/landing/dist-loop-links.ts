/**
 * Canonical Dist Loop public URLs for homepage CTAs (S3).
 * Prefer `main` after release merge; verify live in S5 6.4.
 */

const GITHUB_BLOB = 'https://github.com/adriannoes/asap-protocol/blob/main';
const GITHUB_TREE = 'https://github.com/adriannoes/asap-protocol/tree/main';

/** Build for agents guide (DIST-005 homepage primary). */
export const BUILD_FOR_AGENTS_GUIDE_URL = `${GITHUB_BLOB}/docs/guides/build-for-agents.md`;

/** Thin starter pack index (DIST-003 destinations). */
export const STARTERS_URL = `${GITHUB_TREE}/examples/starters`;

/** v2.5.4 migration note (Dist Loop). */
export const DOCS_MIGRATION_254_URL = `${GITHUB_BLOB}/docs/migration.md#upgrading-from-v253-to-v254`;

/** Changelog anchor for [2.5.4] (GitHub heading slug). */
export const CHANGELOG_254_URL = `${GITHUB_BLOB}/CHANGELOG.md#254---2026-07-18`;
