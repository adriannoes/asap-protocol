/**
 * In-memory rate limiters. Per-instance (serverless) so not distributed across replicas.
 */

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

/**
 * Generic rate limit for user actions (dashboard, register, verify).
 * Returns true if allowed, false if rate limited.
 */
export function checkRateLimit(
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

const PROXY_WINDOW_MS = 60_000;
const PROXY_MAX_PER_WINDOW = 30;
const proxyStore = createStore();

/**
 * IP-based rate limiter for proxy/check endpoint. Prevents abuse.
 */
export function checkProxyRateLimit(
    ip: string
): { allowed: boolean; retryAfter?: number } {
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
