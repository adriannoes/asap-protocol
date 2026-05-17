import { z } from 'zod';

import { HOMEPAGE_CTA_IDS } from '@/lib/telemetry/homepage-cta-ids';

export type CtaMetrics = {
  clicks?: number;
  views?: number;
  ctr?: number;
};

export type SiteMetricsFile = {
  ctr_per_cta?: Record<string, CtaMetrics>;
};

const ctaMetricsSchema = z.object({
  clicks: z.number().int().nonnegative().optional(),
  views: z.number().int().nonnegative().optional(),
  ctr: z.number().min(0).max(1).optional(),
});

const siteMetricsSchema = z.object({
  ctr_per_cta: z.record(z.string(), ctaMetricsSchema).optional(),
});

export function parseSiteMetricsJson(rawJson: string): SiteMetricsFile {
  const parsed: unknown = JSON.parse(rawJson);
  return siteMetricsSchema.parse(parsed);
}

/** Parse optional operator-supplied metrics from env; throws on invalid JSON or schema. */
export function parseOptionalSiteMetricsJsonFromEnv(): SiteMetricsFile | null {
  const raw = process.env.TELEMETRY_SITE_METRICS_JSON?.trim();
  if (!raw) {
    return null;
  }
  return parseSiteMetricsJson(raw);
}

export function computeCtr(metrics: CtaMetrics): CtaMetrics {
  const { clicks, views } = metrics;
  if (typeof clicks === 'number' && typeof views === 'number' && views > 0) {
    return { ...metrics, ctr: clicks / views };
  }
  return { ...metrics };
}

export function mergeCtrPerCta(
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

export function emptyCtrShell(): Record<string, CtaMetrics> {
  const shell: Record<string, CtaMetrics> = {};
  for (const id of HOMEPAGE_CTA_IDS) {
    shell[id] = {};
  }
  return shell;
}
