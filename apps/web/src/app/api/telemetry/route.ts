import { createHash, timingSafeEqual } from 'node:crypto';

import { NextResponse } from 'next/server';

import { HOMEPAGE_CTA_IDS } from '@/lib/telemetry/homepage-cta-ids';
import {
  computeCtr,
  emptyCtrShell,
  mergeCtrPerCta,
  parseOptionalSiteMetricsJsonFromEnv,
} from '@/lib/telemetry/site-metrics';

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

  let parsedEnv;
  try {
    parsedEnv = parseOptionalSiteMetricsJsonFromEnv();
  } catch {
    return NextResponse.json(
      { error: 'Invalid TELEMETRY_SITE_METRICS_JSON (malformed JSON or schema).' },
      { status: 503 },
    );
  }

  const collectedAt = new Date().toISOString();
  const fromEnv = parsedEnv?.ctr_per_cta;

  let shell = emptyCtrShell();
  shell = mergeCtrPerCta(shell, fromEnv ?? undefined);
  const ctrPerCta: Record<string, { clicks?: number; views?: number; ctr?: number }> = {};
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
