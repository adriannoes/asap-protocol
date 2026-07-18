/**
 * Canonical Dist Loop public URLs for homepage CTAs (S3).
 *
 * Guide + starters land on `main` with this release PR; `blob/main` /
 * `tree/main` are the correct post-merge destinations (preview CTAs 404 on
 * GitHub until merge). Migration / changelog stay on `release/2.5.4` until
 * S5 6.4 flip so ribbon pills do not 404 pre-merge.
 */

const GITHUB_BLOB_MAIN = 'https://github.com/adriannoes/asap-protocol/blob/main';
const GITHUB_TREE_MAIN = 'https://github.com/adriannoes/asap-protocol/tree/main';
/** Pre-merge branch for headings not yet on origin/main. */
const GITHUB_BLOB_RELEASE_254 = 'https://github.com/adriannoes/asap-protocol/blob/release/2.5.4';

/** Build for agents guide (DIST-005 homepage primary). */
export const BUILD_FOR_AGENTS_GUIDE_URL = `${GITHUB_BLOB_MAIN}/docs/guides/build-for-agents.md`;

/** Thin starter pack index (DIST-003 destinations). */
export const STARTERS_URL = `${GITHUB_TREE_MAIN}/examples/starters`;

/** v2.5.4 migration note (Dist Loop) — release branch until S5 merge. */
export const DOCS_MIGRATION_254_URL = `${GITHUB_BLOB_RELEASE_254}/docs/migration.md#upgrading-from-v253-to-v254`;

/** Changelog anchor for [2.5.4] — release branch until S5 merge. */
export const CHANGELOG_254_URL = `${GITHUB_BLOB_RELEASE_254}/CHANGELOG.md#254---2026-07-18`;
