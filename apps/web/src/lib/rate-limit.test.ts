import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { checkProxyRateLimit, checkRateLimit } from './rate-limit';

describe('checkProxyRateLimit', () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it('allows the first request for a new IP', async () => {
        const ip = `proxy-first-${Date.now()}-${Math.random()}`;
        await expect(checkProxyRateLimit(ip)).resolves.toEqual({ allowed: true });
    });

    it('blocks the 31st request within the same window', async () => {
        const ip = `proxy-block-${Date.now()}-${Math.random()}`;
        for (let i = 0; i < 30; i++) {
            await expect(checkProxyRateLimit(ip)).resolves.toMatchObject({ allowed: true });
        }
        const blocked = await checkProxyRateLimit(ip);
        expect(blocked.allowed).toBe(false);
        expect(blocked.retryAfter).toBeGreaterThan(0);
    });

    it('resets the counter after the window expires', async () => {
        const ip = `proxy-reset-${Date.now()}-${Math.random()}`;
        for (let i = 0; i < 30; i++) {
            await checkProxyRateLimit(ip);
        }
        await expect(checkProxyRateLimit(ip)).resolves.toMatchObject({ allowed: false });
        vi.advanceTimersByTime(60_001);
        await expect(checkProxyRateLimit(ip)).resolves.toMatchObject({ allowed: true });
    });

    it('isolates limits per IP', async () => {
        const ipA = `proxy-a-${Date.now()}-${Math.random()}`;
        const ipB = `proxy-b-${Date.now()}-${Math.random()}`;
        for (let i = 0; i < 30; i++) {
            await checkProxyRateLimit(ipA);
        }
        await expect(checkProxyRateLimit(ipA)).resolves.toMatchObject({ allowed: false });
        await expect(checkProxyRateLimit(ipB)).resolves.toMatchObject({ allowed: true });
    });
});

describe('checkRateLimit', () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it('allows requests up to maxRequests', async () => {
        const key = `user-${Date.now()}-${Math.random()}`;
        await expect(checkRateLimit(key, 3, 10_000)).resolves.toBe(true);
        await expect(checkRateLimit(key, 3, 10_000)).resolves.toBe(true);
        await expect(checkRateLimit(key, 3, 10_000)).resolves.toBe(true);
        await expect(checkRateLimit(key, 3, 10_000)).resolves.toBe(false);
    });

    it('resets after windowMs', async () => {
        const key = `user-reset-${Date.now()}-${Math.random()}`;
        await expect(checkRateLimit(key, 1, 5_000)).resolves.toBe(true);
        await expect(checkRateLimit(key, 1, 5_000)).resolves.toBe(false);
        vi.advanceTimersByTime(5_001);
        await expect(checkRateLimit(key, 1, 5_000)).resolves.toBe(true);
    });
});
