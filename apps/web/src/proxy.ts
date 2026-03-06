import { NextResponse } from 'next/server';
import { auth } from '@/auth';

export default auth((req) => {
  const isLoggedIn = !!req.auth;
  const { pathname } = req.nextUrl;

  // Apply CORS rules to /api routes (strict: reject missing Origin to enforce allowlist).
  // Skip strict Origin check for /api/auth so NextAuth sign-in, callback, and session work.
  if (pathname.startsWith('/api/') && !pathname.startsWith('/api/auth')) {
    const origin = req.headers.get('origin');
    const allowedOrigin = process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000';

    if (!origin || origin !== allowedOrigin) {
      return NextResponse.json({ error: 'Forbidden' }, { status: 403 });
    }

    const response = NextResponse.next();
    response.headers.set('Access-Control-Allow-Origin', allowedOrigin);
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
});

// Optionally, don't invoke Middleware on some paths
export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
