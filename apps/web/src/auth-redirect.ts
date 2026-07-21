/**
 * Resolves redirect URL for NextAuth redirect callback.
 * Allows same-origin and Agent Builder URL; blocks arbitrary external URLs (open redirect protection).
 * Supports relative URLs for internal app routing.
 */
export function resolveRedirectUrl(url: string, baseUrl: string, agentBuilderUrl?: string): string {
  try {
    if (url.startsWith('//')) {
      return baseUrl;
    }

    // Relative URLs stay on the application origin.
    if (url.startsWith('/')) {
      return new URL(url, baseUrl).toString();
    }

    const urlObj = new URL(url);

    // Exact origin matching for Agent Builder.
    if (agentBuilderUrl) {
      const agentBuilderUrlObj = new URL(agentBuilderUrl);
      if (urlObj.origin === agentBuilderUrlObj.origin) {
        return url;
      }
    }

    // Exact origin matching for the base URL.
    const baseUrlObj = new URL(baseUrl);
    if (urlObj.origin === baseUrlObj.origin) {
      return url;
    }
  } catch {
    // Invalid URL (e.g. malformed), fallback to base
  }
  return baseUrl;
}
