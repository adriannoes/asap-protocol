/** SSRF validation: blocks private IPs, loopback, cloud metadata. */

const BLOCKED_HOSTNAMES = new Set([
    'localhost',
    '127.0.0.1',
    '::1',
    '0.0.0.0',
    'metadata.google.internal',
    'metadata.aws.internal',
    '169.254.169.254',
]);

function isBlockedHostname(hostname: string): boolean {
    const lower = hostname.toLowerCase().replace(/^\[|\]$/g, '');
    if (BLOCKED_HOSTNAMES.has(lower)) return true;
    if (/^::1$/.test(lower) || /^::ffff:/.test(lower)) return true;
    if (/^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.|169\.254\.|0\.)/.test(lower)) return true;
    return false;
}

export interface AllowedUrlResult {
    valid: boolean;
    error?: string;
}

export function isAllowedExternalUrl(url: string): AllowedUrlResult {
    try {
        const parsed = new URL(url);
        if (parsed.protocol !== 'https:' && parsed.protocol !== 'http:') {
            return { valid: false, error: 'URL must use HTTP or HTTPS.' };
        }
        const hostname = parsed.hostname.toLowerCase();
        if (isBlockedHostname(hostname)) {
            return { valid: false, error: 'Internal/Private network addresses are not allowed.' };
        }
        return { valid: true };
    } catch {
        return { valid: false, error: 'Invalid URL.' };
    }
}
