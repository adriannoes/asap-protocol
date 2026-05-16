import { NextResponse } from 'next/server';
import { auth } from '@/auth';

/**
 * Origin allowed for CORS on /api (except auth + fixtures).
 * Production: only NEXT_PUBLIC_APP_URL.
 * Development: that URL or any http(s) Origin on localhost / 127.0.0.1 (any port) so `next dev`
 * on :3001 still works when NEXT_PUBLIC_APP_URL defaults to :3000.
 */
function corsReflectOrigin(requestOrigin: string | null): string | null {
  const configured = process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000';
  if (!requestOrigin) return null;
  if (requestOrigin === configured) return requestOrigin;
  if (process.env.NODE_ENV === 'development') {
    try {
      const url = new URL(requestOrigin);
      if (url.hostname === 'localhost' || url.hostname === '127.0.0.1') {
        return requestOrigin;
      }
    } catch {
      return null;
    }
  }
  return null;
}

export default auth((req) => {
  const isLoggedIn = !!req.auth;
  const { pathname } = req.nextUrl;

  // Apply CORS rules to /api routes (strict: reject missing Origin to enforce allowlist).
  // Skip strict Origin check for /api/auth so NextAuth sign-in, callback, and session work.
  // Skip for /api/fixtures so server-side fetch (e.g. REGISTRY_URL in E2E) can reach it.
  if (pathname.startsWith('/api/') && !pathname.startsWith('/api/auth') && !pathname.startsWith('/api/fixtures')) {
    const origin = req.headers.get('origin');
    const reflect = corsReflectOrigin(origin);

    if (!reflect) {
      return NextResponse.json({ error: 'Forbidden' }, { status: 403 });
    }

    const response = NextResponse.next();
    response.headers.set('Access-Control-Allow-Origin', reflect);
    response.headers.set('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    response.headers.set('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With');
    response.headers.set('Access-Control-Max-Age', '86400');

    if (req.method === 'OPTIONS') {
      return new NextResponse(null, { status: 204, headers: response.headers });
    }
    return response;
  }

  // Protect /dashboard: redirect to sign-in with callbackUrl so after login user lands on requested page
  if (pathname.startsWith('/dashboard') && !isLoggedIn) {
    const callbackUrl = req.nextUrl.toString();
    const signInUrl = new URL('/api/auth/signin', req.nextUrl.origin);
    signInUrl.searchParams.set('callbackUrl', callbackUrl);
    return Response.redirect(signInUrl);
  }

  return NextResponse.next();
});

// Optionally, don't invoke Middleware on some paths
export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
