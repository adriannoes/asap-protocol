import { describe, it, expect, vi, beforeEach } from 'vitest';
import { resolveRedirectUrl } from '../auth-redirect';

const BASE_URL = 'http://localhost:3000';
const AGENT_BUILDER_URL = 'https://open-agentic-flow.vercel.app';

describe('resolveRedirectUrl (auth redirect callback)', () => {
    beforeEach(() => {
        vi.resetModules();
    });

    it('returns Agent Builder URL when url starts with NEXT_PUBLIC_AGENT_BUILDER_URL', () => {
        const url = `${AGENT_BUILDER_URL}?from=asap`;
        const result = resolveRedirectUrl(url, BASE_URL, AGENT_BUILDER_URL);
        expect(result).toBe(url);
    });

    it('returns baseUrl when url is an arbitrary external URL', () => {
        const result = resolveRedirectUrl('https://evil.com/phishing', BASE_URL, AGENT_BUILDER_URL);
        expect(result).toBe(BASE_URL);
    });

    it('returns url when url starts with baseUrl (same origin)', () => {
        const url = `${BASE_URL}/dashboard`;
        const result = resolveRedirectUrl(url, BASE_URL, AGENT_BUILDER_URL);
        expect(result).toBe(url);
    });

    it('returns baseUrl when agentBuilderUrl is undefined (graceful fallback)', () => {
        const externalUrl = `${AGENT_BUILDER_URL}?from=asap`;
        const result = resolveRedirectUrl(externalUrl, BASE_URL, undefined);
        expect(result).toBe(BASE_URL);
    });
});
