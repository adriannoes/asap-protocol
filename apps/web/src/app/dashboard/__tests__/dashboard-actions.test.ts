import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
    fetchUserRegistrationIssues,
    revalidateUserRegistrationIssues,
} from '../actions';
import * as authModule from '@/auth';
import * as rateLimit from '@/lib/rate-limit';
import { cookies } from 'next/headers';
import { getToken } from 'next-auth/jwt';

vi.mock('next/headers', () => ({
    cookies: vi.fn(),
}));

vi.mock('next-auth/jwt', () => ({
    getToken: vi.fn(),
}));

vi.mock('@/auth', () => ({
    auth: vi.fn(),
}));
vi.mock('@/lib/rate-limit', () => ({
    checkRateLimit: vi.fn(() => true),
}));

vi.mock('next/cache', () => ({
    unstable_cache: (fn: () => Promise<unknown>) => fn,
    revalidateTag: vi.fn(),
}));

const mockListForRepo = vi.fn();
vi.mock('octokit', () => ({
    Octokit: class MockOctokit {
        rest = {
            issues: {
                listForRepo: mockListForRepo,
            },
        };
    },
}));

const auth = vi.mocked(authModule.auth);
const checkRateLimit = vi.mocked(rateLimit.checkRateLimit);
const mockCookies = vi.mocked(cookies);
const mockGetToken = vi.mocked(getToken);

describe('fetchUserRegistrationIssues', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        auth.mockResolvedValue({
            user: { id: 'u1', username: 'testuser' },
        } as never);

        // @ts-expect-error type override for testing
        mockCookies.mockResolvedValue({
            get: vi.fn().mockReturnValue({ value: 'fake-session-cookie' })
        });
        mockGetToken.mockResolvedValue({ accessToken: 'ghp_fake_token' });

        checkRateLimit.mockReturnValue(true);
    });

    it('returns error when not authenticated', async () => {
        auth.mockResolvedValue(null as never);
        const result = await fetchUserRegistrationIssues();
        expect(result.success).toBe(false);
        if (!result.success) expect(result.error).toBe('Unauthorized');
    });

    it('returns error when rate limit exceeded', async () => {
        checkRateLimit.mockReturnValue(false);
        const result = await fetchUserRegistrationIssues();
        expect(result.success).toBe(false);
        if (!result.success) expect(result.error).toContain('Too many requests');
    });

    it('returns error when username or encrypted token missing', async () => {
        mockGetToken.mockResolvedValue(null);
        const result = await fetchUserRegistrationIssues();
        expect(result.success).toBe(false);
        if (!result.success) expect(result.error).toMatch(/Missing GitHub credentials/);
    });

    it('returns success with user registration issues (happy path)', async () => {
        auth.mockResolvedValue({
            user: { id: 'u1', username: 'testuser' },
        } as never);

        mockListForRepo.mockResolvedValue({
            data: [
                {
                    id: 123,
                    number: 42,
                    title: 'Register: my-agent',
                    html_url: 'https://github.com/owner/repo/issues/42',
                    state: 'open',
                    user: { login: 'testuser' },
                    pull_request: undefined,
                },
            ],
            headers: {},
        });

        const result = await fetchUserRegistrationIssues();

        expect(result.success).toBe(true);
        if (result.success) {
            // @ts-expect-error test assertion simplifies result object access
            const data = result.data;
            expect(data).toBeDefined();
            expect(data).toHaveLength(1);
            expect(data[0]).toEqual({
                id: 123,
                number: 42,
                title: 'Register: my-agent',
                url: 'https://github.com/owner/repo/issues/42',
                state: 'open',
                status: 'Pending',
            });
        }
    });

    it('revalidateUserRegistrationIssues does not throw when authenticated', async () => {
        auth.mockResolvedValue({
            user: { id: 'u1', username: 'testuser' },
        } as never);
        await expect(revalidateUserRegistrationIssues()).resolves.not.toThrow();
    });

    it('revalidateUserRegistrationIssues does nothing when not authenticated', async () => {
        auth.mockResolvedValue(null as never);
        await expect(revalidateUserRegistrationIssues()).resolves.not.toThrow();
    });
});
