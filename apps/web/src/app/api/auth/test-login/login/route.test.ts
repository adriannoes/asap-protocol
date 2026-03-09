import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { GET } from './route';
import { encode } from 'next-auth/jwt';

const cookiesMock = vi.fn();
const setCookieMock = vi.fn();

vi.mock('next-auth/jwt', () => ({
  encode: vi.fn(),
}));

vi.mock('next/headers', () => ({
  cookies: (...args: unknown[]) => cookiesMock(...args),
}));

const originalEnableFixtureRoutes = process.env.ENABLE_FIXTURE_ROUTES;
const originalNodeEnv = process.env.NODE_ENV;
const originalAuthSecret = process.env.AUTH_SECRET;

describe('GET /api/auth/test-login/login', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    cookiesMock.mockResolvedValue({ set: setCookieMock });
    vi.mocked(encode).mockResolvedValue('encoded-token');
    process.env.AUTH_SECRET = 'a'.repeat(40);
  });

  afterEach(() => {
    if (originalEnableFixtureRoutes === undefined) {
      delete process.env.ENABLE_FIXTURE_ROUTES;
    } else {
      process.env.ENABLE_FIXTURE_ROUTES = originalEnableFixtureRoutes;
    }

    if (originalNodeEnv === undefined) {
      delete process.env.NODE_ENV;
    } else {
      process.env.NODE_ENV = originalNodeEnv;
    }

    if (originalAuthSecret === undefined) {
      delete process.env.AUTH_SECRET;
    } else {
      process.env.AUTH_SECRET = originalAuthSecret;
    }
  });

  it('returns 404 when fixture routes are disabled', async () => {
    process.env.ENABLE_FIXTURE_ROUTES = 'false';
    process.env.NODE_ENV = 'test';

    const res = await GET(new Request('http://localhost/api/auth/test-login/login'));

    expect(res.status).toBe(404);
    expect(await res.json()).toEqual({ error: 'Not found' });
    expect(encode).not.toHaveBeenCalled();
    expect(cookiesMock).not.toHaveBeenCalled();
  });

  it('returns 404 in production even when fixture flag is true', async () => {
    process.env.ENABLE_FIXTURE_ROUTES = 'true';
    process.env.NODE_ENV = 'production';

    const res = await GET(new Request('http://localhost/api/auth/test-login/login'));

    expect(res.status).toBe(404);
    expect(await res.json()).toEqual({ error: 'Not found' });
    expect(encode).not.toHaveBeenCalled();
  });

  it('creates secure cookie and redirects when request is https', async () => {
    process.env.ENABLE_FIXTURE_ROUTES = 'true';
    process.env.NODE_ENV = 'test';

    const request = new Request(
      'https://example.com/api/auth/test-login/login?id=u-1&username=alice&redirect=%2Fdashboard%2Fverify'
    );

    const res = await GET(request);

    expect(encode).toHaveBeenCalledWith({
      token: expect.objectContaining({
        sub: 'u-1',
        id: 'u-1',
        username: 'alice',
      }),
      secret: process.env.AUTH_SECRET,
      salt: '__Secure-authjs.session-token',
    });

    expect(setCookieMock).toHaveBeenCalledWith('__Secure-authjs.session-token', 'encoded-token', {
      httpOnly: true,
      sameSite: 'lax',
      path: '/',
      secure: true,
    });

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('https://example.com/dashboard/verify');
  });

  it('uses default values and non-secure cookie on http requests', async () => {
    process.env.ENABLE_FIXTURE_ROUTES = 'true';
    process.env.NODE_ENV = 'test';

    const res = await GET(new Request('http://localhost/api/auth/test-login/login'));

    expect(encode).toHaveBeenCalledWith({
      token: expect.objectContaining({
        sub: 'test-user-123',
        id: 'test-user-123',
        username: 'test-e2e-user',
      }),
      secret: process.env.AUTH_SECRET,
      salt: 'authjs.session-token',
    });

    expect(setCookieMock).toHaveBeenCalledWith('authjs.session-token', 'encoded-token', {
      httpOnly: true,
      sameSite: 'lax',
      path: '/',
      secure: false,
    });

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('http://localhost/dashboard');
  });
});
