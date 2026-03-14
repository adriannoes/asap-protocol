import { NextResponse } from 'next/server';
import { signIn } from '@/auth';

export async function GET(request: Request) {
    if (process.env.ENABLE_FIXTURE_ROUTES !== 'true') {
        return NextResponse.json({ error: 'Not found' }, { status: 404 });
    }

    const { searchParams } = new URL(request.url);
    const username = searchParams.get('username') || 'test-e2e-user';
    const redirectUrl = searchParams.get('redirect') || '/dashboard';

    await signIn('test-login', { username, redirectTo: redirectUrl });

    return NextResponse.json({ success: true });
}
