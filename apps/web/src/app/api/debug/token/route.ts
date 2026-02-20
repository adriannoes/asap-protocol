import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@/auth';
import { getToken } from 'next-auth/jwt';

/** Debug: verify access token in JWT. 404 in production; optional X-Debug-Token when DEBUG_TOKEN set. */
export async function GET(request: NextRequest) {
  const isProduction =
    process.env.NODE_ENV === 'production' || process.env.VERCEL_ENV === 'production';
  if (isProduction) {
    return NextResponse.json({ error: 'Not found' }, { status: 404 });
  }

  const debugToken = process.env.DEBUG_TOKEN;
  if (debugToken) {
    const headerToken = request.headers.get('X-Debug-Token');
    if (headerToken !== debugToken) {
      return NextResponse.json({ error: 'Not found' }, { status: 404 });
    }
  }

  const session = await auth();
  if (!session?.user) {
    return NextResponse.json({ hasToken: false, error: 'Not authenticated' }, { status: 401 });
  }

  const token = await getToken({
    req: request,
    secret: process.env.AUTH_SECRET,
    salt: 'authjs.session-token',
  });

  const hasToken = !!(token && typeof (token as { accessToken?: string }).accessToken === 'string');
  return NextResponse.json({ hasToken, username: token?.username ?? session?.user?.name });
}
