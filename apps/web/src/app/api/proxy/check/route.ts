import { NextRequest, NextResponse } from 'next/server';
import { isAllowedProxyUrlAsync } from '@/lib/url-validator-server';
import { checkProxyRateLimit } from '@/lib/rate-limit';

const FETCH_TIMEOUT_MS = 3000;

function getClientIp(request: NextRequest): string {
    const forwarded = request.headers.get('x-forwarded-for');
    if (forwarded) return forwarded.split(',')[0]?.trim() ?? 'unknown';
    const realIp = request.headers.get('x-real-ip');
    if (realIp) return realIp;
    return 'unknown';
}

export async function GET(request: NextRequest) {
    const url = request.nextUrl.searchParams.get('url');
    if (!url || typeof url !== 'string') {
        return NextResponse.json({ error: 'Missing url parameter' }, { status: 400 });
    }

    const ip = getClientIp(request);
    const rateCheck = checkProxyRateLimit(ip);
    if (!rateCheck.allowed) {
        return NextResponse.json(
            { error: 'Too many requests', retryAfter: rateCheck.retryAfter },
            { status: 429, headers: rateCheck.retryAfter ? { 'Retry-After': String(rateCheck.retryAfter) } : undefined }
        );
    }

    const check = await isAllowedProxyUrlAsync(url);
    if (!check.valid) {
        return NextResponse.json({ error: check.error ?? 'Invalid URL' }, { status: 400 });
    }

    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
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
