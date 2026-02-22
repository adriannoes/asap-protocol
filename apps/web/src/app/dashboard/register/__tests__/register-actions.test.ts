import { describe, it, expect, vi, beforeEach } from 'vitest';
import { submitAgentRegistration } from '../actions';
import * as authModule from '@/auth';
import * as urlValidator from '@/lib/url-validator';
import * as rateLimit from '@/lib/rate-limit';

vi.mock('@/auth', () => ({
    auth: vi.fn(),
}));
vi.mock('@/lib/url-validator', () => ({
    isAllowedExternalUrl: vi.fn(),
}));
vi.mock('@/lib/rate-limit', () => ({
    checkRateLimit: vi.fn(() => true),
}));

const auth = vi.mocked(authModule.auth);
const isAllowedExternalUrl = vi.mocked(urlValidator.isAllowedExternalUrl);
const checkRateLimit = vi.mocked(rateLimit.checkRateLimit);

const validForm = {
    name: 'my-agent',
    description: 'A test agent for integration.',
    manifest_url: 'https://example.com/manifest.json',
    endpoint_http: 'https://example.com/asap',
    endpoint_ws: '',
    skills: 'search,summarize',
    built_with: '',
    repository_url: '',
    documentation_url: '',
    confirm: true as const,
};

describe('submitAgentRegistration', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        auth.mockResolvedValue({
            user: { id: 'u1', username: 'testuser', name: 'Test' },
        } as never);
        isAllowedExternalUrl.mockReturnValue({ valid: true });
        checkRateLimit.mockReturnValue(true);
    });

    it('returns error when not authenticated', async () => {
        auth.mockResolvedValue(null as never);
        const result = await submitAgentRegistration(validForm);
        expect(result.success).toBe(false);
        expect(result.error).toContain('logged in');
    });

    it('returns error when username missing', async () => {
        auth.mockResolvedValue({ user: { id: 'u1' } } as never);
        const result = await submitAgentRegistration(validForm);
        expect(result.success).toBe(false);
        expect(result.error).toMatch(/GitHub account link missing|re-login/);
    });

    it('returns error when rate limit exceeded', async () => {
        checkRateLimit.mockReturnValue(false);
        const result = await submitAgentRegistration(validForm);
        expect(result.success).toBe(false);
        expect(result.error).toContain('Too many registration attempts');
    });

    it('returns error for invalid form data', async () => {
        const result = await submitAgentRegistration({
            ...validForm,
            name: 'ab', // too short
        });
        expect(result.success).toBe(false);
        expect(result.error).toContain('Invalid form data');
    });

    it('returns error when manifest URL fails SSRF check', async () => {
        isAllowedExternalUrl.mockImplementation((url: string) => {
            if (url.includes('manifest')) return { valid: false, error: 'Internal/Private network addresses are not allowed.' };
            return { valid: true };
        });
        const result = await submitAgentRegistration(validForm);
        expect(result.success).toBe(false);
        expect(result.error).toContain('Manifest URL');
        expect(result.error).toContain('Internal/Private');
    });

    it('returns error when endpoint URL fails SSRF check', async () => {
        isAllowedExternalUrl.mockImplementation((url: string) => {
            if (url.includes('asap')) return { valid: false, error: 'Internal/Private network addresses are not allowed.' };
            return { valid: true };
        });
        const result = await submitAgentRegistration(validForm);
        expect(result.success).toBe(false);
        expect(result.error).toContain('Endpoint URL');
    });

    it('returns error when WebSocket URL fails SSRF check', async () => {
        const formWithWs = { ...validForm, endpoint_ws: 'wss://169.254.169.254/internal' };
        isAllowedExternalUrl.mockImplementation((url: string) => {
            if (url.includes('169.254') || url.includes('internal'))
                return { valid: false, error: 'Internal/Private network addresses are not allowed.' };
            return { valid: true };
        });
        const result = await submitAgentRegistration(formWithWs);
        expect(result.success).toBe(false);
        expect(result.error).toContain('WebSocket URL');
    });

    it('returns error when manifest URL is not reachable (HEAD returns non-ok)', async () => {
        const originalFetch = globalThis.fetch;
        globalThis.fetch = vi.fn().mockResolvedValue({ ok: false, status: 404 });
        try {
            const result = await submitAgentRegistration(validForm);
            expect(result.success).toBe(false);
            expect(result.error).toContain('Manifest URL returned status 404');
            expect(result.error).toContain('Must be reachable');
        } finally {
            globalThis.fetch = originalFetch;
        }
    });

    it('returns error when manifest URL fetch throws (network error)', async () => {
        const originalFetch = globalThis.fetch;
        globalThis.fetch = vi.fn().mockRejectedValue(new Error('ECONNREFUSED'));
        try {
            const result = await submitAgentRegistration(validForm);
            expect(result.success).toBe(false);
            expect(result.error).toContain('Could not reach Manifest URL');
            expect(result.error).toContain('ECONNREFUSED');
        } finally {
            globalThis.fetch = originalFetch;
        }
    });

    it('returns success and correct GitHub Issue URL when validation and reachability pass', async () => {
        const originalFetch = globalThis.fetch;
        globalThis.fetch = vi.fn().mockResolvedValue({ ok: true });
        try {
            const result = await submitAgentRegistration(validForm);
            expect(result.success).toBe(true);
            expect('issueUrl' in result && result.issueUrl).toBeTruthy();
            const url = (result as { issueUrl: string }).issueUrl;
            expect(url).toContain('/issues/new');
            expect(url).toContain('template=register_agent.yml');
            expect(url).toContain('title=Register');
            expect(url).toContain('name=my-agent');
            expect(url).toContain('manifest_url=');
            expect(url).toContain('http_endpoint=');
            expect(url).toContain('skills=search%2Csummarize');
        } finally {
            globalThis.fetch = originalFetch;
        }
    });
});
