import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { mockLimit } = vi.hoisted(() => ({
    mockLimit: vi.fn(),
}));

vi.mock('@upstash/redis', () => ({
    Redis: class MockRedis {},
}));

vi.mock('@upstash/ratelimit', () => {
    class MockRatelimit {
        limit = mockLimit;
        static fixedWindow = vi.fn(() => 'fixed-window');
        static slidingWindow = vi.fn(() => 'sliding-window');
    }
    return { Ratelimit: MockRatelimit };
});

describe('rate-limit Redis backend', () => {
    beforeEach(() => {
        vi.resetModules();
        mockLimit.mockReset();
        delete process.env.KV_REST_API_URL;
        delete process.env.KV_REST_API_TOKEN;
        delete process.env.UPSTASH_REDIS_REST_URL;
        delete process.env.UPSTASH_REDIS_REST_TOKEN;
    });

    afterEach(() => {
        delete process.env.KV_REST_API_URL;
        delete process.env.KV_REST_API_TOKEN;
        delete process.env.UPSTASH_REDIS_REST_URL;
        delete process.env.UPSTASH_REDIS_REST_TOKEN;
    });

    it('allows when Upstash limiter succeeds', async () => {
        process.env.UPSTASH_REDIS_REST_URL = 'https://example.upstash.io';
        process.env.UPSTASH_REDIS_REST_TOKEN = 'test-token';
        mockLimit.mockResolvedValue({ success: true, reset: Date.now() + 60_000 });

        const { checkRateLimit } = await import('./rate-limit');
        await expect(checkRateLimit('redis-user-key', 3, 10_000)).resolves.toBe(true);
        expect(mockLimit).toHaveBeenCalledWith('redis-user-key');
    });

    it('blocks proxy traffic when limiter returns failure with retryAfter', async () => {
        process.env.UPSTASH_REDIS_REST_URL = 'https://example.upstash.io';
        process.env.UPSTASH_REDIS_REST_TOKEN = 'test-token';
        const resetAt = Date.now() + 45_000;
        mockLimit.mockResolvedValue({ success: false, reset: resetAt });

        const { checkProxyRateLimit } = await import('./rate-limit');
        const result = await checkProxyRateLimit('203.0.113.1');
        expect(result.allowed).toBe(false);
        expect(result.retryAfter).toBeGreaterThan(0);
    });

    it('falls back to in-memory limits when Redis throws', async () => {
        process.env.UPSTASH_REDIS_REST_URL = 'https://example.upstash.io';
        process.env.UPSTASH_REDIS_REST_TOKEN = 'test-token';
        mockLimit.mockRejectedValue(new Error('redis unavailable'));

        const { checkRateLimit } = await import('./rate-limit');
        const key = `fallback-${Date.now()}`;
        await expect(checkRateLimit(key, 1, 60_000)).resolves.toBe(true);
        await expect(checkRateLimit(key, 1, 60_000)).resolves.toBe(false);
    });

    it('ignores mixed Upstash URL with KV token', async () => {
        process.env.UPSTASH_REDIS_REST_URL = 'https://example.upstash.io';
        process.env.KV_REST_API_TOKEN = 'kv-only-token';

        const { checkRateLimit } = await import('./rate-limit');
        const key = `misconfig-${Date.now()}`;
        await expect(checkRateLimit(key, 2, 10_000)).resolves.toBe(true);
        expect(mockLimit).not.toHaveBeenCalled();
    });
});
