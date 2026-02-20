/** In-memory rate limiter; resets on serverless cold start. */

const rateLimitMap = new Map<string, { count: number; resetAt: number }>();

export function checkRateLimit(
    userId: string,
    maxRequests = 5,
    windowMs = 60_000
): boolean {
    const now = Date.now();
    const entry = rateLimitMap.get(userId);
    if (!entry || now > entry.resetAt) {
        rateLimitMap.set(userId, { count: 1, resetAt: now + windowMs });
        return true;
    }
    if (entry.count >= maxRequests) return false;
    entry.count++;
    return true;
}
