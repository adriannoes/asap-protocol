import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { HOMEPAGE_CTA_IDS } from '@/lib/telemetry/homepage-cta-ids';
import {
  computeCtr,
  emptyCtrShell,
  mergeCtrPerCta,
  parseOptionalSiteMetricsJsonFromEnv,
  parseSiteMetricsJson,
} from '@/lib/telemetry/site-metrics';

describe('site-metrics', () => {
  describe('parseSiteMetricsJson', () => {
    it('accepts empty object', () => {
      expect(parseSiteMetricsJson('{}')).toEqual({});
    });

    it('parses ctr_per_cta entries', () => {
      const raw = JSON.stringify({
        ctr_per_cta: { 'docs-openapi': { clicks: 2, views: 10 } },
      });
      const got = parseSiteMetricsJson(raw);
      expect(got.ctr_per_cta?.['docs-openapi']?.clicks).toBe(2);
    });

    it('rejects invalid ctr range', () => {
      const raw = JSON.stringify({
        ctr_per_cta: { x: { ctr: 2 } },
      });
      expect(() => parseSiteMetricsJson(raw)).toThrow();
    });
  });

  describe('parseOptionalSiteMetricsJsonFromEnv', () => {
    const original = process.env.TELEMETRY_SITE_METRICS_JSON;

    beforeEach(() => {
      delete process.env.TELEMETRY_SITE_METRICS_JSON;
    });

    afterEach(() => {
      if (original === undefined) {
        delete process.env.TELEMETRY_SITE_METRICS_JSON;
      } else {
        process.env.TELEMETRY_SITE_METRICS_JSON = original;
      }
    });

    it('returns null when unset or whitespace', () => {
      expect(parseOptionalSiteMetricsJsonFromEnv()).toBeNull();
      process.env.TELEMETRY_SITE_METRICS_JSON = '   ';
      expect(parseOptionalSiteMetricsJsonFromEnv()).toBeNull();
    });

    it('parses when set', () => {
      process.env.TELEMETRY_SITE_METRICS_JSON = '{"ctr_per_cta":{}}';
      expect(parseOptionalSiteMetricsJsonFromEnv()).toEqual({ ctr_per_cta: {} });
    });
  });

  describe('computeCtr', () => {
    it('computes ctr when views > 0', () => {
      expect(computeCtr({ clicks: 3, views: 12 })).toEqual({
        clicks: 3,
        views: 12,
        ctr: 0.25,
      });
    });

    it('passes through when views missing or zero', () => {
      expect(computeCtr({ clicks: 3 })).toEqual({ clicks: 3 });
      expect(computeCtr({})).toEqual({});
    });
  });

  describe('mergeCtrPerCta', () => {
    it('merges env over base keys', () => {
      const base = { a: { views: 1 } };
      const merged = mergeCtrPerCta(base, { a: { clicks: 2 }, b: { views: 3 } });
      expect(merged.a).toEqual({ views: 1, clicks: 2 });
      expect(merged.b).toEqual({ views: 3 });
    });

    it('returns copy when fromEnv absent', () => {
      const base = { a: { clicks: 1 } };
      const merged = mergeCtrPerCta(base);
      expect(merged).toEqual(base);
      expect(merged).not.toBe(base);
    });
  });

  describe('emptyCtrShell', () => {
    it('includes every homepage CTA id', () => {
      const shell = emptyCtrShell();
      for (const id of HOMEPAGE_CTA_IDS) {
        expect(shell[id]).toEqual({});
      }
      expect(Object.keys(shell).length).toBe(HOMEPAGE_CTA_IDS.length);
    });
  });
});
