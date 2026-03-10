import { afterEach, describe, expect, it, vi } from 'vitest';
import { GET } from './route';
import { signIn } from '@/auth';

vi.mock('@/auth', () => ({
  signIn: vi.fn(),
}));

const originalEnableFixtureRoutes = process.env.ENABLE_FIXTURE_ROUTES;

function createRequest(query = ''): Request {
  return new Request(`http://localhost/api/auth/test-login${query}`, { method: 'GET' });
}

describe('GET /api/auth/test-login', () => {
  afterEach(() => {
    vi.clearAllMocks();
    if (originalEnableFixtureRoutes === undefined) {
      delete process.env.ENABLE_FIXTURE_ROUTES;
    } else {
      process.env.ENABLE_FIXTURE_ROUTES = originalEnableFixtureRoutes;
    }
  });

  it('returns 404 when fixture routes are disabled', async () => {
    process.env.ENABLE_FIXTURE_ROUTES = 'false';
    const res = await GET(createRequest());
    expect(res.status).toBe(404);
    expect(await res.json()).toEqual({ error: 'Not found' });
    expect(signIn).not.toHaveBeenCalled();
  });

  it('calls signIn with query params when fixture routes are enabled', async () => {
    process.env.ENABLE_FIXTURE_ROUTES = 'true';
    vi.mocked(signIn).mockResolvedValue(undefined as never);

    const res = await GET(createRequest('?username=alice&redirect=%2Fdashboard%2Fregister'));

    expect(signIn).toHaveBeenCalledWith('test-login', {
      username: 'alice',
      redirectTo: '/dashboard/register',
    });
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ success: true });
  });

  it('uses default username and redirect when query params are missing', async () => {
    process.env.ENABLE_FIXTURE_ROUTES = 'true';
    vi.mocked(signIn).mockResolvedValue(undefined as never);

    const res = await GET(createRequest());

    expect(signIn).toHaveBeenCalledWith('test-login', {
      username: 'test-e2e-user',
      redirectTo: '/dashboard',
    });
    expect(res.status).toBe(200);
  });
});
