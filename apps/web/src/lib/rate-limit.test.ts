import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { checkProxyRateLimit, checkRateLimit } from './rate-limit';

describe('checkProxyRateLimit', () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it('allows the first request for a new IP', () => {
        const ip = `proxy-first-${Date.now()}-${Math.random()}`;
        expect(checkProxyRateLimit(ip)).toEqual({ allowed: true });
    });

    it('blocks the 31st request within the same window', () => {
        const ip = `proxy-block-${Date.now()}-${Math.random()}`;
        for (let i = 0; i < 30; i++) {
            expect(checkProxyRateLimit(ip).allowed).toBe(true);
        }
        const blocked = checkProxyRateLimit(ip);
        expect(blocked.allowed).toBe(false);
        expect(blocked.retryAfter).toBeGreaterThan(0);
    });

    it('resets the counter after the window expires', () => {
        const ip = `proxy-reset-${Date.now()}-${Math.random()}`;
        for (let i = 0; i < 30; i++) {
            checkProxyRateLimit(ip);
        }
        expect(checkProxyRateLimit(ip).allowed).toBe(false);
        vi.advanceTimersByTime(60_001);
        expect(checkProxyRateLimit(ip).allowed).toBe(true);
    });

    it('isolates limits per IP', () => {
        const ipA = `proxy-a-${Date.now()}-${Math.random()}`;
        const ipB = `proxy-b-${Date.now()}-${Math.random()}`;
        for (let i = 0; i < 30; i++) {
            checkProxyRateLimit(ipA);
        }
        expect(checkProxyRateLimit(ipA).allowed).toBe(false);
        expect(checkProxyRateLimit(ipB).allowed).toBe(true);
    });
});

describe('checkRateLimit', () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it('allows requests up to maxRequests', () => {
        const key = `user-${Date.now()}-${Math.random()}`;
        expect(checkRateLimit(key, 3, 10_000)).toBe(true);
        expect(checkRateLimit(key, 3, 10_000)).toBe(true);
        expect(checkRateLimit(key, 3, 10_000)).toBe(true);
        expect(checkRateLimit(key, 3, 10_000)).toBe(false);
    });

    it('resets after windowMs', () => {
        const key = `user-reset-${Date.now()}-${Math.random()}`;
        expect(checkRateLimit(key, 1, 5_000)).toBe(true);
        expect(checkRateLimit(key, 1, 5_000)).toBe(false);
        vi.advanceTimersByTime(5_001);
        expect(checkRateLimit(key, 1, 5_000)).toBe(true);
    });
});
