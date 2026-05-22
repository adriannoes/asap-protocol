import { NextResponse } from 'next/server';
import { signIn } from '@/auth';
import { resolveRedirectUrl } from '@/auth-redirect';
import { TestLoginQuerySchema, parseSearchParams } from '@/lib/api-schemas';

export async function GET(request: Request) {
    if (
        process.env.ENABLE_FIXTURE_ROUTES !== 'true' ||
        process.env.NODE_ENV === 'production'
    ) {
        return NextResponse.json({ error: 'Not found' }, { status: 404 });
    }

    const { searchParams } = new URL(request.url);
    const parsed = parseSearchParams(TestLoginQuerySchema, searchParams);
    if (!parsed.success) {
        return NextResponse.json({ error: parsed.error }, { status: 400 });
    }

    const username = parsed.data.username ?? 'test-e2e-user';
    const requestUrl = new URL(request.url);
    const safeRedirect = resolveRedirectUrl(
        parsed.data.redirect,
        requestUrl.origin,
        process.env.AGENT_BUILDER_URL
    );

    await signIn('test-login', { username, redirectTo: safeRedirect });

    return NextResponse.json({ success: true });
}
