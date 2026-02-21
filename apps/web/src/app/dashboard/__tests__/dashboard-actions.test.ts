import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fetchUserRegistrationIssues } from '../actions';
import * as authModule from '@/auth';
import * as rateLimit from '@/lib/rate-limit';

vi.mock('@/auth', () => ({
    auth: vi.fn(),
    decryptToken: vi.fn(),
}));
vi.mock('@/lib/rate-limit', () => ({
    checkRateLimit: vi.fn(() => true),
}));
vi.mock('octokit', () => ({ Octokit: vi.fn() }));

const auth = vi.mocked(authModule.auth);
const checkRateLimit = vi.mocked(rateLimit.checkRateLimit);

describe('fetchUserRegistrationIssues', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        auth.mockResolvedValue({
            user: { id: 'u1', username: 'testuser' },
            encryptedAccessToken: 'encrypted-token',
        } as never);
        checkRateLimit.mockReturnValue(true);
    });

    it('returns error when not authenticated', async () => {
        auth.mockResolvedValue(null as never);
        const result = await fetchUserRegistrationIssues();
        expect(result.success).toBe(false);
        expect(result.error).toBe('Unauthorized');
    });

    it('returns error when rate limit exceeded', async () => {
        checkRateLimit.mockReturnValue(false);
        const result = await fetchUserRegistrationIssues();
        expect(result.success).toBe(false);
        expect(result.error).toContain('Too many requests');
    });

    it('returns error when username or encrypted token missing', async () => {
        auth.mockResolvedValue({ user: { id: 'u1' }, encryptedAccessToken: null } as never);
        const result = await fetchUserRegistrationIssues();
        expect(result.success).toBe(false);
        expect(result.error).toMatch(/Missing GitHub credentials/);
    });
});
