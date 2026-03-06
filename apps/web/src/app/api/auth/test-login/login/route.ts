import { NextResponse } from 'next/server';
import { encode } from 'next-auth/jwt';
import { cookies } from 'next/headers';

export async function GET(request: Request) {
    // Strictly deny access outside fixture-enabled non-production environments
    if (process.env.ENABLE_FIXTURE_ROUTES !== 'true' || process.env.NODE_ENV === 'production') {
        return NextResponse.json({ error: 'Not found' }, { status: 404 });
    }

    const { searchParams } = new URL(request.url);
    const userId = searchParams.get('id') || 'test-user-123';
    const username = searchParams.get('username') || 'test-e2e-user';
    const redirectUrl = searchParams.get('redirect') || '/dashboard';

    const isSecure = request.url.startsWith('https://');
    const cookieName = isSecure ? '__Secure-authjs.session-token' : 'authjs.session-token';

    // Generate a NextAuth valid JWT token
    const token = await encode({
        token: {
            sub: userId,
            id: userId,
            username: username,
            name: 'E2E Test User',
            email: 'e2e@example.com',
            accessToken: 'mock-access-token-12345',
        },
        secret: process.env.AUTH_SECRET as string,
        salt: cookieName,
    });

    const cookieStore = await cookies();
    cookieStore.set(cookieName, token, {
        httpOnly: true,
        sameSite: 'lax',
        path: '/',
        secure: isSecure,
    });

    return NextResponse.redirect(new URL(redirectUrl, request.url));
}
