/**
 * Canonical Dist Loop public URLs for homepage CTAs (S3).
 *
 * Guide, starters, migration, and changelog land on `main` with this release
 * PR; `blob/main` / `tree/main` are the correct post-merge destinations
 * (preview CTAs 404 on GitHub until merge).
 */

/** GitHub `blob/main` base — reuse for docs links across Dist Loop surfaces. */
export const GITHUB_BLOB_MAIN = 'https://github.com/adriannoes/asap-protocol/blob/main';

/** GitHub `tree/main` base — reuse for directory links (starters, examples). */
export const GITHUB_TREE_MAIN = 'https://github.com/adriannoes/asap-protocol/tree/main';

/**
 * Build a canonical `blob/main` URL for a repo-relative path.
 *
 * Example: `githubBlobMain('docs/migration.md#anchor')`
 */
export function githubBlobMain(repoPath: string): string {
  const normalized = repoPath.replace(/^\//, '');
  return `${GITHUB_BLOB_MAIN}/${normalized}`;
}

/**
 * Build a canonical `tree/main` URL for a repo-relative directory path.
 *
 * Example: `githubTreeMain('examples/starters')`
 */
export function githubTreeMain(repoPath: string): string {
  const normalized = repoPath.replace(/^\//, '');
  return `${GITHUB_TREE_MAIN}/${normalized}`;
}

/** Build for agents guide (DIST-005 homepage primary). */
export const BUILD_FOR_AGENTS_GUIDE_URL = githubBlobMain('docs/guides/build-for-agents.md');

/** Thin starter pack index (DIST-003 destinations). */
export const STARTERS_URL = githubTreeMain('examples/starters');

/** v2.5.4 migration note (Dist Loop). */
export const DOCS_MIGRATION_254_URL = githubBlobMain(
  'docs/migration.md#upgrading-from-v253-to-v254'
);

/** Changelog anchor for [2.5.4]. */
export const CHANGELOG_254_URL = githubBlobMain('CHANGELOG.md#254---2026-07-18');
