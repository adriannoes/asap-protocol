/**
 * Resolves redirect URL for NextAuth redirect callback.
 * Allows same-origin and Agent Builder URL; blocks arbitrary external URLs (open redirect protection).
 * Supports relative URLs for internal app routing.
 */
export function resolveRedirectUrl(
    url: string,
    baseUrl: string,
    agentBuilderUrl?: string
): string {
    try {
        // 1. Handle relative URLs (essential for local app UX)
        if (url.startsWith('/')) {
            return new URL(url, baseUrl).toString();
        }

        const urlObj = new URL(url);

        // 2. Exact origin matching for Agent Builder
        if (agentBuilderUrl) {
            const agentBuilderUrlObj = new URL(agentBuilderUrl);
            if (urlObj.origin === agentBuilderUrlObj.origin) {
                return url;
            }
        }

        // 3. Exact origin matching for base URL
        const baseUrlObj = new URL(baseUrl);
        if (urlObj.origin === baseUrlObj.origin) {
            return url;
        }
    } catch {
        // Invalid URL (e.g. malformed), fallback to base
    }
    return baseUrl;
}
