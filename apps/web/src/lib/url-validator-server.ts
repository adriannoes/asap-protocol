import { promises as dns } from 'node:dns';
import { isAllowedProxyUrl, AllowedUrlResult } from './url-validator';

function parseIPv4ToNumber(ip: string): number | null {
    const parts = ip.split('.');
    if (parts.length !== 4) return null;
    let n = 0;
    for (const p of parts) {
        const octet = parseInt(p, 10);
        if (Number.isNaN(octet) || octet < 0 || octet > 255) return null;
        n = (n << 8) | octet;
    }
    return n >>> 0;
}

function isBlockedIPv4(ip: string): boolean {
    const n = parseIPv4ToNumber(ip);
    if (n === null) return true;
    if ((n >>> 24) === 127) return true; // 127.0.0.0/8
    if ((n >>> 24) === 10) return true; // 10.0.0.0/8
    if ((n >>> 20) === 0xac1) return true; // 172.16.0.0/12
    if ((n >>> 16) === 0xc0a8) return true; // 192.168.0.0/16
    if ((n >>> 16) === 0xa9fe) return true; // 169.254.0.0/16
    if ((n >>> 24) === 0) return true; // 0.0.0.0/8
    return false;
}

function isBlockedIPv6(ip: string): boolean {
    const lower = ip.toLowerCase();
    if (lower === '::1') return true;
    if (lower.startsWith('fe80:')) return true; // fe80::/10
    if (lower.startsWith('fc') || lower.startsWith('fd')) return true; // fc00::/7
    if (lower.startsWith('::ffff:')) {
        const embedded = lower.slice(7);
        return isBlockedIPv4(embedded);
    }
    return false;
}

export async function isAllowedProxyUrlAsync(url: string): Promise<AllowedUrlResult> {
    const sync = isAllowedProxyUrl(url);
    if (!sync.valid) return sync;

    try {
        const parsed = new URL(url);
        const hostname = parsed.hostname.replace(/^\[|\]$/g, '');

        const [v4, v6] = await Promise.allSettled([
            dns.resolve4(hostname),
            dns.resolve6(hostname),
        ]);

        const ips: string[] = [];
        if (v4.status === 'fulfilled' && Array.isArray(v4.value)) ips.push(...v4.value);
        if (v6.status === 'fulfilled' && Array.isArray(v6.value)) ips.push(...v6.value);
        if (ips.length === 0) {
            return { valid: false, error: 'Could not resolve hostname.' };
        }

        for (const ip of ips) {
            if (ip.includes('.')) {
                if (isBlockedIPv4(ip)) {
                    return { valid: false, error: 'Internal/Private network addresses are not allowed.' };
                }
            } else {
                if (isBlockedIPv6(ip)) {
                    return { valid: false, error: 'Internal/Private network addresses are not allowed.' };
                }
            }
        }
        return { valid: true };
    } catch {
        return { valid: false, error: 'Invalid URL.' };
    }
}
