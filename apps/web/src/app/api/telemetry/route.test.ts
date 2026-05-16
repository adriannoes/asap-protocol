import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { GET } from './route';

const originalEnv: Record<string, string | undefined> = {};

function saveEnv(key: string): void {
  if (!(key in originalEnv)) {
    originalEnv[key] = process.env[key];
  }
}

function createRequest(headers?: Record<string, string>): Request {
  return new Request('http://localhost/api/telemetry', {
    method: 'GET',
    headers: headers ?? {},
  });
}

describe('GET /api/telemetry', () => {
  beforeEach(() => {
    saveEnv('TELEMETRY_TOKEN');
    saveEnv('TELEMETRY_SITE_METRICS_JSON');
    process.env.TELEMETRY_TOKEN = 'test-telemetry-token';
    delete process.env.TELEMETRY_SITE_METRICS_JSON;
  });

  afterEach(() => {
    for (const [k, v] of Object.entries(originalEnv)) {
      if (v === undefined) {
        delete process.env[k];
      } else {
        process.env[k] = v;
      }
    }
  });

  it('returns 503 when TELEMETRY_TOKEN is unset', async () => {
    delete process.env.TELEMETRY_TOKEN;
    const res = await GET(createRequest());
    expect(res.status).toBe(503);
  });

  it('returns 401 when Authorization is missing or invalid', async () => {
    const missing = await GET(createRequest());
    expect(missing.status).toBe(401);

    const bad = await GET(createRequest({ Authorization: 'Bearer wrong' }));
    expect(bad.status).toBe(401);
  });

  it('returns ctr_per_cta with merged env metrics when authorized', async () => {
    process.env.TELEMETRY_SITE_METRICS_JSON = JSON.stringify({
      ctr_per_cta: {
        'docs-typescript': { clicks: 10, views: 100 },
      },
    });
    const res = await GET(
      createRequest({ Authorization: 'Bearer test-telemetry-token' }),
    );
    expect(res.status).toBe(200);
    const json = (await res.json()) as {
      site: { ctr_per_cta: Record<string, { ctr?: number; clicks?: number }> };
    };
    expect(json.site.ctr_per_cta['docs-typescript']?.clicks).toBe(10);
    expect(json.site.ctr_per_cta['docs-typescript']?.ctr).toBeCloseTo(0.1);
  });
});
