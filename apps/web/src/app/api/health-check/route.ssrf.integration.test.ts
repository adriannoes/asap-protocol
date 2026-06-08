import { beforeEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { GET } from './route';
import { checkProxyRateLimit } from '@/lib/rate-limit';

vi.mock('@/lib/rate-limit', () => ({
  checkProxyRateLimit: vi.fn(),
}));

function createRequest(url: string): NextRequest {
  const base = 'http://localhost/api/health-check';
  return new NextRequest(`${base}?url=${encodeURIComponent(url)}`, { method: 'GET' });
}

describe('GET /api/health-check', () => {
  beforeEach(() => {
    vi.mocked(checkProxyRateLimit).mockReturnValue({ allowed: true });
  });

  it('returns 400 for loopback URL 127.0.0.2', async () => {
    const res = await GET(createRequest('http://127.0.0.2:8080/health'));
    expect(res.status).toBe(400);
    const json = await res.json();
    expect(json.error).toContain('Internal/Private');
  });
});
