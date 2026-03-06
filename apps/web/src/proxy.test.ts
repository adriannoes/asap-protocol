/** Proxy middleware: CORS /api and dashboard → sign-in redirect. */
import { describe, it, expect, vi } from 'vitest';
import { NextRequest } from 'next/server';

// Mock auth so the default export is our handler (no session logic in tests)
vi.mock('@/auth', () => ({
    auth: (fn: (req: NextRequest & { auth?: unknown }) => Response) => fn,
}));

const baseUrl = 'http://localhost:3000';

/** Compatible with Next.js AppRouteHandlerFnContext (second arg to proxy). */
const middlewareContext = { params: Promise.resolve({}) };

function createRequest(
    pathname: string,
    options: { origin?: string; method?: string; auth?: unknown } = {}
): NextRequest & { auth?: unknown } {
    const url = new URL(pathname, baseUrl);
    const headers = new Headers();
    if (options.origin) headers.set('origin', options.origin);
    const req = new NextRequest(url.toString(), {
        method: options.method ?? 'GET',
        headers,
    }) as NextRequest & { auth?: unknown };
    if (options.auth !== undefined) req.auth = options.auth;
    return req;
}

describe('proxy (middleware)', () => {
    describe('CORS for /api (non-auth)', () => {
        it('returns 403 when Origin is missing for /api/proxy/check', async () => {
            const { default: proxy } = await import('@/proxy');
            const req = createRequest('/api/proxy/check');
            const res = (await proxy(req, middlewareContext)) as Response;
            expect(res.status).toBe(403);
            const json = await res.json();
            expect(json.error).toBe('Forbidden');
        });

        it('returns 403 when Origin does not match allowed', async () => {
            const { default: proxy } = await import('@/proxy');
            const req = createRequest('/api/health-check', { origin: 'https://evil.com' });
            const res = (await proxy(req, middlewareContext)) as Response;
            expect(res.status).toBe(403);
            const json = await res.json();
            expect(json.error).toBe('Forbidden');
        });

        it('allows request when Origin matches localhost', async () => {
            const { default: proxy } = await import('@/proxy');
            const req = createRequest('/api/health-check', { origin: 'http://localhost:3000' });
            const res = (await proxy(req, middlewareContext)) as Response;
            expect(res.status).toBe(200);
        });
    });

    describe('/api/auth excluded from strict CORS', () => {
        it('does not return 403 for /api/auth/signin when Origin is missing', async () => {
            const { default: proxy } = await import('@/proxy');
            const req = createRequest('/api/auth/signin');
            const res = (await proxy(req, middlewareContext)) as Response;
            // Pass-through (undefined) or any non-403 response; auth routes must not be blocked
            expect(res === undefined || (res && res.status !== 403)).toBe(true);
        });

        it('does not return 403 for /api/auth/callback when Origin is missing', async () => {
            const { default: proxy } = await import('@/proxy');
            const req = createRequest('/api/auth/callback/github');
            const res = (await proxy(req, middlewareContext)) as Response;
            expect(res === undefined || (res && res.status !== 403)).toBe(true);
        });

        it('does not return 403 for /api/auth/session when Origin differs', async () => {
            const { default: proxy } = await import('@/proxy');
            const req = createRequest('/api/auth/session', { origin: 'https://other.com' });
            const res = (await proxy(req, middlewareContext)) as Response;
            expect(res === undefined || (res && res.status !== 403)).toBe(true);
        });
    });

    describe('dashboard redirect to sign-in with callbackUrl', () => {
        it('redirects unauthenticated user from /dashboard/register to sign-in with callbackUrl', async () => {
            const { default: proxy } = await import('@/proxy');
            const req = createRequest('/dashboard/register');
            const res = (await proxy(req, middlewareContext)) as Response;
            expect(res.status).toBe(302);
            const location = res.headers.get('Location');
            expect(location).toBeDefined();
            const signInUrl = new URL(location!);
            expect(signInUrl.pathname).toBe('/api/auth/signin');
            const callbackUrl = signInUrl.searchParams.get('callbackUrl');
            expect(callbackUrl).toBe(`${baseUrl}/dashboard/register`);
        });

        it('redirects unauthenticated user from /dashboard to sign-in with callbackUrl', async () => {
            const { default: proxy } = await import('@/proxy');
            const req = createRequest('/dashboard');
            const res = (await proxy(req, middlewareContext)) as Response;
            expect(res.status).toBe(302);
            const location = res.headers.get('Location');
            expect(location).toBeDefined();
            const signInUrl = new URL(location!);
            expect(signInUrl.pathname).toBe('/api/auth/signin');
            expect(signInUrl.searchParams.get('callbackUrl')).toBe(`${baseUrl}/dashboard`);
        });

        it('redirects unauthenticated user from /dashboard/verify to sign-in with callbackUrl', async () => {
            const { default: proxy } = await import('@/proxy');
            const req = createRequest('/dashboard/verify');
            const res = (await proxy(req, middlewareContext)) as Response;
            expect(res.status).toBe(302);
            const location = res.headers.get('Location');
            const signInUrl = new URL(location!);
            expect(signInUrl.pathname).toBe('/api/auth/signin');
            expect(signInUrl.searchParams.get('callbackUrl')).toBe(`${baseUrl}/dashboard/verify`);
        });

        it('allows request to /dashboard when authenticated (next)', async () => {
            const { default: proxy } = await import('@/proxy');
            const req = createRequest('/dashboard/register', { auth: { user: { id: '1' } } });
            const res = (await proxy(req, middlewareContext)) as Response;
            // Pass-through (undefined) or 200; no redirect when logged in
            expect(res === undefined || (res && res.status === 200)).toBe(true);
            if (res && res.headers.get('Location')) {
                expect(res.headers.get('Location')).not.toContain('/api/auth/signin');
            }
        });
    });
});
