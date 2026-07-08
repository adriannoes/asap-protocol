/**
 * Rate limiters for dashboard actions and proxy endpoints.
 * Uses Upstash Redis / Vercel KV when configured; otherwise in-memory per instance.
 */

import { Ratelimit } from '@upstash/ratelimit';
import { Redis } from '@upstash/redis';

interface Entry {
    count: number;
    resetAt: number;
}

function createStore() {
    const store = new Map<string, Entry>();

    function prune(): void {
        const now = Date.now();
        for (const [key, entry] of store.entries()) {
            if (entry.resetAt < now) store.delete(key);
        }
    }

    return { store, prune };
}

const userStore = createStore();
const proxyStore = createStore();

const PROXY_WINDOW_MS = 60_000;
const PROXY_MAX_PER_WINDOW = 30;

let redisClient: Redis | null | undefined;

function getRedisClient(): Redis | null {
    if (redisClient !== undefined) return redisClient;

    const url = process.env.UPSTASH_REDIS_REST_URL ?? process.env.KV_REST_API_URL;
    const token =
        process.env.UPSTASH_REDIS_REST_TOKEN ?? process.env.KV_REST_API_TOKEN;

    if (!url || !token) {
        redisClient = null;
        return null;
    }

    redisClient = new Redis({ url, token });
    return redisClient;
}

const userLimiterCache = new Map<string, Ratelimit>();
let proxyLimiter: Ratelimit | null = null;

function windowLabel(windowMs: number): string {
    const seconds = Math.max(1, Math.ceil(windowMs / 1000));
    return `${seconds} s`;
}

function getUserLimiter(maxRequests: number, windowMs: number): Ratelimit {
    const redis = getRedisClient();
    if (!redis) {
        throw new Error('Redis client is not configured');
    }

    const cacheKey = `${maxRequests}:${windowMs}`;
    const cached = userLimiterCache.get(cacheKey);
    if (cached) return cached;

    const limiter = new Ratelimit({
        redis,
        limiter: Ratelimit.slidingWindow(maxRequests, windowLabel(windowMs)),
        prefix: 'asap:web:rl:user',
    });
    userLimiterCache.set(cacheKey, limiter);
    return limiter;
}

function getProxyLimiter(): Ratelimit {
    const redis = getRedisClient();
    if (!redis) {
        throw new Error('Redis client is not configured');
    }

    if (!proxyLimiter) {
        proxyLimiter = new Ratelimit({
            redis,
            limiter: Ratelimit.slidingWindow(
                PROXY_MAX_PER_WINDOW,
                windowLabel(PROXY_WINDOW_MS)
            ),
            prefix: 'asap:web:rl:proxy',
        });
    }
    return proxyLimiter;
}

function checkRateLimitInMemory(
    key: string,
    maxRequests: number,
    windowMs: number
): boolean {
    userStore.prune();
    const now = Date.now();
    const entry = userStore.store.get(key);

    if (!entry) {
        userStore.store.set(key, { count: 1, resetAt: now + windowMs });
        return true;
    }

    if (entry.resetAt < now) {
        userStore.store.set(key, { count: 1, resetAt: now + windowMs });
        return true;
    }

    entry.count++;
    return entry.count <= maxRequests;
}

function checkProxyRateLimitInMemory(ip: string): {
    allowed: boolean;
    retryAfter?: number;
} {
    proxyStore.prune();
    const now = Date.now();
    const entry = proxyStore.store.get(ip);

    if (!entry) {
        proxyStore.store.set(ip, { count: 1, resetAt: now + PROXY_WINDOW_MS });
        return { allowed: true };
    }

    if (entry.resetAt < now) {
        proxyStore.store.set(ip, { count: 1, resetAt: now + PROXY_WINDOW_MS });
        return { allowed: true };
    }

    entry.count++;
    if (entry.count > PROXY_MAX_PER_WINDOW) {
        return {
            allowed: false,
            retryAfter: Math.ceil((entry.resetAt - now) / 1000),
        };
    }
    return { allowed: true };
}

/**
 * Generic rate limit for user actions (dashboard, register, verify).
 * Returns true if allowed, false if rate limited.
 */
export async function checkRateLimit(
    key: string,
    maxRequests: number,
    windowMs: number
): Promise<boolean> {
    if (!getRedisClient()) {
        return checkRateLimitInMemory(key, maxRequests, windowMs);
    }

    try {
        const limiter = getUserLimiter(maxRequests, windowMs);
        const result = await limiter.limit(key);
        return result.success;
    } catch (error) {
        console.error(
            JSON.stringify({
                event: 'rate_limit.redis_fallback',
                scope: 'user',
                error: error instanceof Error ? error.message : String(error),
            })
        );
        return checkRateLimitInMemory(key, maxRequests, windowMs);
    }
}

/**
 * IP-based rate limiter for proxy/check endpoint. Prevents abuse.
 */
export async function checkProxyRateLimit(
    ip: string
): Promise<{ allowed: boolean; retryAfter?: number }> {
    if (!getRedisClient()) {
        return checkProxyRateLimitInMemory(ip);
    }

    try {
        const limiter = getProxyLimiter();
        const result = await limiter.limit(ip);
        if (result.success) {
            return { allowed: true };
        }
        const retryAfter =
            result.reset > 0
                ? Math.max(1, Math.ceil((result.reset - Date.now()) / 1000))
                : undefined;
        return { allowed: false, retryAfter };
    } catch (error) {
        console.error(
            JSON.stringify({
                event: 'rate_limit.redis_fallback',
                scope: 'proxy',
                error: error instanceof Error ? error.message : String(error),
            })
        );
        return checkProxyRateLimitInMemory(ip);
    }
}
