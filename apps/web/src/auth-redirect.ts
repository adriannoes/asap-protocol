/**
 * Resolves redirect URL for NextAuth redirect callback.
 * Allows same-origin and Agent Builder URL; blocks arbitrary external URLs (open redirect protection).
 */
export function resolveRedirectUrl(
    url: string,
    baseUrl: string,
    agentBuilderUrl?: string
): string {
    if (agentBuilderUrl && url.startsWith(agentBuilderUrl)) {
        return url;
    }
    if (url.startsWith(baseUrl)) return url;
    return baseUrl;
}
