import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { GET } from './route';

describe('GET /api/fixtures/registry', () => {
  beforeEach(() => {
    vi.stubEnv('ENABLE_FIXTURE_ROUTES', 'true');
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('returns 404 when fixture routes are disabled', async () => {
    vi.stubEnv('ENABLE_FIXTURE_ROUTES', 'false');
    const res = await GET(new NextRequest('http://localhost/api/fixtures/registry'));
    expect(res.status).toBe(404);
  });

  it('returns agents with default count', async () => {
    const res = await GET(new NextRequest('http://localhost/api/fixtures/registry'));
    expect(res.status).toBe(200);
    const json = await res.json();
    expect(Array.isArray(json)).toBe(true);
    expect(json.length).toBe(500);
  });

  it('returns 400 for invalid count', async () => {
    const res = await GET(new NextRequest('http://localhost/api/fixtures/registry?count=abc'));
    expect(res.status).toBe(400);
    expect(await res.json()).toEqual({ error: 'Invalid input' });
  });

  it('returns 400 when count exceeds max', async () => {
    const res = await GET(new NextRequest('http://localhost/api/fixtures/registry?count=99999'));
    expect(res.status).toBe(400);
  });
});
