import { describe, it, expect, vi, beforeEach } from 'vitest';
import { NextRequest } from 'next/server';
import { GET } from '../route';
import { isAllowedProxyUrlAsync } from '@/lib/url-validator-server';

vi.mock('@/lib/url-validator-server');

function createRequest(targetUrl: string, headers?: Record<string, string>): NextRequest {
    return new NextRequest(
        `http://localhost/api/proxy/check?url=${encodeURIComponent(targetUrl)}`,
        { method: 'GET', headers: headers ?? {} }
    );
}

describe('GET /api/proxy/check', () => {
    beforeEach(() => {
        vi.mocked(isAllowedProxyUrlAsync).mockResolvedValue({ valid: true });
    });

    it('returns 400 when url parameter is missing', async () => {
        const req = new NextRequest('http://localhost/api/proxy/check', { method: 'GET' });
        const res = await GET(req);
        expect(res.status).toBe(400);
        const json = await res.json();
        expect(json.error).toContain('Missing url');
    });

    it('returns 400 for HTTP URL (HTTPS only)', async () => {
        vi.mocked(isAllowedProxyUrlAsync).mockResolvedValueOnce({ valid: false, error: 'URL must use HTTPS only.' });
        const req = createRequest('http://example.com/health');
        const res = await GET(req);
        expect(res.status).toBe(400);
        const json = await res.json();
        expect(json.error).toContain('HTTPS');
    });

    it('returns 400 when URL resolves to private IP (DNS rebinding)', async () => {
        vi.mocked(isAllowedProxyUrlAsync).mockResolvedValueOnce({
            valid: false,
            error: 'Internal/Private network addresses are not allowed.',
        });
        const req = createRequest('https://attacker.example.com/health');
        const res = await GET(req);
        expect(res.status).toBe(400);
        const json = await res.json();
        expect(json.error).toContain('Private');
    });

    it('returns 400 for private IP hostname literal', async () => {
        vi.mocked(isAllowedProxyUrlAsync).mockResolvedValueOnce({ valid: false, error: 'Internal/Private network addresses are not allowed.' });
        const req = createRequest('https://192.168.1.1/health');
        const res = await GET(req);
        expect(res.status).toBe(400);
        const json = await res.json();
        expect(json.error).toBeDefined();
    });

    it('returns 400 for localhost', async () => {
        vi.mocked(isAllowedProxyUrlAsync).mockResolvedValueOnce({ valid: false, error: 'Internal/Private network addresses are not allowed.' });
        const req = createRequest('https://localhost/health');
        const res = await GET(req);
        expect(res.status).toBe(400);
    });

    it('returns ok:true when target returns 200', async () => {
        vi.stubGlobal(
            'fetch',
            vi.fn().mockResolvedValue({ ok: true, status: 200 })
        );
        const req = createRequest('https://example.com/health');
        const res = await GET(req);
        expect(res.status).toBe(200);
        const json = await res.json();
        expect(json.ok).toBe(true);
        expect(json.status).toBe(200);
    });

    it('returns ok:false when target returns 404', async () => {
        vi.stubGlobal(
            'fetch',
            vi.fn().mockResolvedValue({ ok: false, status: 404 })
        );
        const req = createRequest('https://example.com/health');
        const res = await GET(req);
        expect(res.status).toBe(200);
        const json = await res.json();
        expect(json.ok).toBe(false);
        expect(json.status).toBe(404);
    });

    it('returns ok:false when fetch throws', async () => {
        vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('ECONNREFUSED')));
        const req = createRequest('https://example.com/health');
        const res = await GET(req);
        expect(res.status).toBe(200);
        const json = await res.json();
        expect(json.ok).toBe(false);
        expect(json.status).toBe(0);
    });
});
