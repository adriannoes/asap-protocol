import { NextResponse } from 'next/server';
import { signIn } from '@/auth';

export async function GET(request: Request) {
    // SECURITY: Strictly deny access unless the fixture flag is explicitly provided.
    if (process.env.ENABLE_FIXTURE_ROUTES !== 'true') {
        return NextResponse.json({ error: 'Not found' }, { status: 404 });
    }

    const { searchParams } = new URL(request.url);
    const username = searchParams.get('username') || 'test-e2e-user';
    const redirectUrl = searchParams.get('redirect') || '/dashboard';

    // Let NextAuth handle the entire session creation process natively
    await signIn('test-login', { username, redirectTo: redirectUrl });

    // Should not reach here if signIn redirects, but just in case
    return NextResponse.json({ success: true });
}
