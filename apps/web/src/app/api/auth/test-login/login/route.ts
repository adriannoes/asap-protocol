import { NextResponse } from 'next/server';
import { encode } from 'next-auth/jwt';
import { cookies } from 'next/headers';
import { resolveRedirectUrl } from '@/auth-redirect';
import { TestLoginQuerySchema, parseSearchParams } from '@/lib/api-schemas';

export async function GET(request: Request) {
    if (process.env.ENABLE_FIXTURE_ROUTES !== 'true' || process.env.NODE_ENV === 'production') {
        return NextResponse.json({ error: 'Not found' }, { status: 404 });
    }

    const { searchParams } = new URL(request.url);
    const parsed = parseSearchParams(TestLoginQuerySchema, searchParams);
    if (!parsed.success) {
        return NextResponse.json({ error: parsed.error }, { status: 400 });
    }

    const userId = parsed.data.id ?? 'test-user-123';
    const username = parsed.data.username ?? 'test-e2e-user';
    const requestUrl = new URL(request.url);
    const safeRedirect = resolveRedirectUrl(
        parsed.data.redirect,
        requestUrl.origin,
        process.env.AGENT_BUILDER_URL
    );

    const isSecure = request.url.startsWith('https://');
    const cookieName = isSecure ? '__Secure-authjs.session-token' : 'authjs.session-token';

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

    return NextResponse.redirect(safeRedirect);
}
