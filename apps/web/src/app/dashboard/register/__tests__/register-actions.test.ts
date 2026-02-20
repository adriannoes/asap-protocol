import { describe, it, expect, vi, beforeEach } from 'vitest';
import { submitAgentRegistration } from '../actions';
import * as authModule from '@/auth';
import * as urlValidator from '@/lib/url-validator';
import * as rateLimit from '@/lib/rate-limit';

vi.mock('@/auth', () => ({
    auth: vi.fn(),
    decryptToken: vi.fn(),
}));
vi.mock('@/lib/url-validator', () => ({
    isAllowedExternalUrl: vi.fn(),
}));
vi.mock('@/lib/rate-limit', () => ({
    checkRateLimit: vi.fn(() => true),
}));
vi.mock('octokit', () => ({ Octokit: vi.fn() }));

const auth = vi.mocked(authModule.auth);
const decryptToken = vi.mocked(authModule.decryptToken);
const isAllowedExternalUrl = vi.mocked(urlValidator.isAllowedExternalUrl);
const checkRateLimit = vi.mocked(rateLimit.checkRateLimit);

const validForm = {
    name: 'my-agent',
    description: 'A test agent for integration.',
    manifest_url: 'https://example.com/manifest.json',
    endpoint_http: 'https://example.com/asap',
    endpoint_ws: '',
    skills: 'search,summarize',
};

describe('submitAgentRegistration', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        auth.mockResolvedValue({
            user: { id: 'u1', username: 'testuser', name: 'Test' },
            encryptedAccessToken: 'encrypted-token',
        } as never);
        decryptToken.mockResolvedValue('ghp_test');
        isAllowedExternalUrl.mockReturnValue({ valid: true });
        checkRateLimit.mockReturnValue(true);
    });

    it('returns error when not authenticated', async () => {
        auth.mockResolvedValue(null as never);
        const result = await submitAgentRegistration(validForm);
        expect(result.success).toBe(false);
        expect(result.error).toContain('logged in');
        expect(decryptToken).not.toHaveBeenCalled();
    });

    it('returns error when username or encrypted token missing', async () => {
        auth.mockResolvedValue({ user: { id: 'u1' }, encryptedAccessToken: null } as never);
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
});
