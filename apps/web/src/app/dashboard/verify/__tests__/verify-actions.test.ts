import { describe, it, expect, vi, beforeEach } from 'vitest';
import { submitVerificationRequest } from '../actions';
import * as authModule from '@/auth';
import { buildVerificationRequestIssueUrl } from '@/lib/github-issues';
import type { VerificationFormValues } from '@/lib/github-issues';

vi.mock('@/auth', () => ({
    auth: vi.fn(),
}));

const auth = vi.mocked(authModule.auth);

const validFormValues: VerificationFormValues = {
    agent_id: 'urn:asap:agent:username:my-agent',
    why_verified: 'Running in production for 3 months with 99.5% uptime.',
    running_since: '2 months',
};

describe('submitVerificationRequest', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        auth.mockResolvedValue({
            user: { id: 'u1', username: 'testuser', name: 'Test' },
        } as never);
    });

    it('returns error when not authenticated', async () => {
        auth.mockResolvedValue(null as never);
        const result = await submitVerificationRequest(validFormValues);
        expect(result.success).toBe(false);
        expect(result.error).toBe('Unauthorized');
    });

    it('returns error when session has no user', async () => {
        auth.mockResolvedValue({} as never);
        const result = await submitVerificationRequest(validFormValues);
        expect(result.success).toBe(false);
        expect(result.error).toBe('Unauthorized');
    });

    it('returns success and correct GitHub Issue URL when authenticated', async () => {
        const result = await submitVerificationRequest(validFormValues);
        expect(result.success).toBe(true);
        expect('issueUrl' in result && result.issueUrl).toBeTruthy();
        const url = (result as { issueUrl: string }).issueUrl;
        expect(url).toContain('/issues/new');
        expect(url).toContain('template=request_verification.yml');
        expect(url).toContain('title=Verify');
        expect(url).toContain('agent_id=');
        expect(url).toContain('why_verified=');
        expect(url).toContain('running_since=');
    });

    it('builds URL matching buildVerificationRequestIssueUrl output', async () => {
        const result = await submitVerificationRequest(validFormValues);
        expect(result.success).toBe(true);
        const url = (result as { issueUrl: string }).issueUrl;

        const owner = process.env.GITHUB_REGISTRY_OWNER || 'adriannoes';
        const repo = process.env.GITHUB_REGISTRY_REPO || 'asap-protocol';
        const expectedUrl = buildVerificationRequestIssueUrl(validFormValues, { owner, repo });
        expect(url).toBe(expectedUrl);
    });

    it('includes optional evidence and contact in URL when provided', async () => {
        const valuesWithOptional: VerificationFormValues = {
            ...validFormValues,
            evidence: 'https://status.example.com',
            contact: '@maintainer',
        };
        const result = await submitVerificationRequest(valuesWithOptional);
        expect(result.success).toBe(true);
        const url = (result as { issueUrl: string }).issueUrl;
        expect(url).toContain('evidence=');
        expect(url).toContain('contact=');
    });
});
