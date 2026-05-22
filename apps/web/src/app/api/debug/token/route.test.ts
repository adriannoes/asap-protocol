import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { GET } from './route';

vi.mock('@/auth', () => ({
  auth: vi.fn(),
}));

vi.mock('next-auth/jwt', () => ({
  getToken: vi.fn(),
}));

import { auth } from '@/auth';
import { getToken } from 'next-auth/jwt';

describe('GET /api/debug/token', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubEnv('DEBUG_TOKEN', 'debug-secret');
    vi.stubEnv('AUTH_SECRET', 'a'.repeat(40));
    vi.stubEnv('NODE_ENV', 'test');
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('returns 404 in production', async () => {
    vi.stubEnv('NODE_ENV', 'production');
    const res = await GET(new NextRequest('http://localhost/api/debug/token'));
    expect(res.status).toBe(404);
  });

  it('returns 404 when debug token header is wrong', async () => {
    const res = await GET(
      new NextRequest('http://localhost/api/debug/token', {
        headers: { 'X-Debug-Token': 'wrong' },
      })
    );
    expect(res.status).toBe(404);
  });

  it('returns 401 when session is missing', async () => {
    vi.mocked(auth).mockResolvedValue(null as never);
    const res = await GET(
      new NextRequest('http://localhost/api/debug/token', {
        headers: { 'X-Debug-Token': 'debug-secret' },
      })
    );
    expect(res.status).toBe(401);
    expect(await res.json()).toEqual({ hasToken: false, error: 'Not authenticated' });
  });

  it('returns hasToken when authenticated with valid debug header', async () => {
    vi.mocked(auth).mockResolvedValue({ user: { name: 'alice' } } as never);
    vi.mocked(getToken).mockResolvedValue({ accessToken: 'tok', username: 'alice' } as never);

    const res = await GET(
      new NextRequest('http://localhost/api/debug/token', {
        headers: { 'X-Debug-Token': 'debug-secret' },
      })
    );

    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ hasToken: true, username: 'alice' });
  });
});
