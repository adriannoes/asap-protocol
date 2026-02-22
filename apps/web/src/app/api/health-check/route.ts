/**
 * Server-side proxy for agent health checks.
 * Prevents client IP exposure to arbitrary agent endpoints (IMP-6).
 * Validates URL for SSRF before fetching.
 */
import { NextRequest, NextResponse } from 'next/server';
import { isAllowedExternalUrl } from '@/lib/url-validator';

export async function GET(request: NextRequest) {
    const url = request.nextUrl.searchParams.get('url');
    if (!url || typeof url !== 'string') {
        return NextResponse.json({ error: 'Missing url parameter' }, { status: 400 });
    }

    const check = isAllowedExternalUrl(url);
    if (!check.valid) {
        return NextResponse.json({ error: check.error ?? 'Invalid URL' }, { status: 400 });
    }

    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 3000);
        const res = await fetch(url, {
            method: 'GET',
            signal: controller.signal,
        });
        clearTimeout(timeoutId);
        return NextResponse.json({ ok: res.ok, status: res.status });
    } catch {
        return NextResponse.json({ ok: false, status: 0 });
    }
}
