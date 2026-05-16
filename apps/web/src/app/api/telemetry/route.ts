import { createHash, timingSafeEqual } from 'node:crypto';

import { NextResponse } from 'next/server';

/**
 * Server-only telemetry snapshot for weekly aggregation (S1 adoption telemetry).
 *
 * **Vercel Web Analytics limitation:** Vercel does not ship a public REST API to read
 * aggregated page views / custom events / `data-cta` click breakdowns as of 2026.
 * Dashboard CSV export, [Web Analytics Drains](https://vercel.com/docs/analytics/web-analytics-drains),
 * or a future API would be required for fully automated CTR without an intermediate store.
 *
 * For CI and operators, optional env **`TELEMETRY_SITE_METRICS_JSON`** may hold JSON shaped as
 * `{ "ctr_per_cta": { "docs-typescript": { "clicks": 10, "views": 100 } } }` (pasted from an
 * export or another backend). This is **not** a secret; keep tokens in `TELEMETRY_TOKEN` only.
 *
 * Required: **`TELEMETRY_TOKEN`** — send `Authorization: Bearer <TELEMETRY_TOKEN>`.
 * Token comparison uses fixed-length SHA-256 digests (timingSafeEqual) to reduce timing leaks.
 */
export const runtime = 'nodejs';

/** Known homepage `data-cta` values (keep in sync with landing components). */
const HOMEPAGE_CTA_IDS = [
  'hero-release-badge',
  'hero-explore-agents',
  'hero-register-agent',
  'docs-openapi',
  'docs-typescript',
  'docs-auto-registration',
  'docs-capabilities-escalation',
  'feature-openapi-adapter',
  'feature-typescript-sdk',
  'feature-auto-registration',
  'feature-lite-registry',
  'feature-verified-trust',
  'feature-1-click-integration',
  'feature-full-observability',
  'feature-per-agent-identity',
  'feature-scoped-capabilities',
  'feature-streaming-responses',
  'release-changelog-github',
] as const;

type CtaMetrics = {
  clicks?: number;
  views?: number;
  ctr?: number;
};

type SiteMetricsFile = {
  ctr_per_cta?: Record<string, CtaMetrics>;
};

function tokensEqual(provided: string, expected: string): boolean {
  const left = createHash('sha256').update(provided, 'utf8').digest();
  const right = createHash('sha256').update(expected, 'utf8').digest();
  return timingSafeEqual(left, right);
}

function parseBearerToken(request: Request): string | null {
  const raw = request.headers.get('authorization');
  if (!raw) {
    return null;
  }
  const prefix = 'bearer ';
  if (!raw.toLowerCase().startsWith(prefix)) {
    return null;
  }
  return raw.slice(prefix.length).trim();
}

function computeCtr(metrics: CtaMetrics): CtaMetrics {
  const { clicks, views } = metrics;
  if (typeof clicks === 'number' && typeof views === 'number' && views > 0) {
    return { ...metrics, ctr: clicks / views };
  }
  return { ...metrics };
}

function mergeCtrPerCta(
  base: Record<string, CtaMetrics>,
  fromEnv?: Record<string, CtaMetrics>,
): Record<string, CtaMetrics> {
  const out: Record<string, CtaMetrics> = { ...base };
  if (!fromEnv) {
    return out;
  }
  for (const [k, v] of Object.entries(fromEnv)) {
    out[k] = { ...(out[k] ?? {}), ...v };
  }
  return out;
}

function parseOptionalSiteMetricsJson(): SiteMetricsFile | null {
  const raw = process.env.TELEMETRY_SITE_METRICS_JSON?.trim();
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw) as SiteMetricsFile;
  } catch {
    return null;
  }
}

function emptyCtrShell(): Record<string, CtaMetrics> {
  const shell: Record<string, CtaMetrics> = {};
  for (const id of HOMEPAGE_CTA_IDS) {
    shell[id] = {};
  }
  return shell;
}

export async function GET(request: Request): Promise<NextResponse> {
  const expected = process.env.TELEMETRY_TOKEN?.trim() ?? '';
  if (!expected) {
    return NextResponse.json(
      { error: 'TELEMETRY_TOKEN is not configured on the server.' },
      { status: 503 },
    );
  }

  const provided = parseBearerToken(request);
  if (!provided || !tokensEqual(provided, expected)) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const collectedAt = new Date().toISOString();
  const parsed = parseOptionalSiteMetricsJson();
  const fromEnv = parsed?.ctr_per_cta;

  let shell = emptyCtrShell();
  shell = mergeCtrPerCta(shell, fromEnv ?? undefined);
  const ctrPerCta: Record<string, CtaMetrics> = {};
  for (const [k, v] of Object.entries(shell)) {
    ctrPerCta[k] = computeCtr(v);
  }

  const hasEnvMetrics = Boolean(fromEnv && Object.keys(fromEnv).length > 0);

  return NextResponse.json({
    collected_at: collectedAt,
    site: {
      ctr_per_cta: ctrPerCta,
      homepage_cta_ids: [...HOMEPAGE_CTA_IDS],
      vercel_web_analytics: {
        api_for_aggregates: 'unavailable_public_rest',
        note: hasEnvMetrics
          ? 'Merged metrics from TELEMETRY_SITE_METRICS_JSON (operator-supplied).'
          : 'No operator metrics env set; counts are empty until TELEMETRY_SITE_METRICS_JSON is provided, a drain is configured, or Vercel exposes an analytics query API.',
      },
    },
  });
}
