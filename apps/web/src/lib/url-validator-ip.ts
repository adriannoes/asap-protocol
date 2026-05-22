export const BLOCKED_HOSTNAMES = new Set([
    'localhost',
    '127.0.0.1',
    '::1',
    '0.0.0.0',
    'metadata.google.internal',
    'metadata.aws.internal',
    '169.254.169.254',
]);

export function parseIPv4ToNumber(ip: string): number | null {
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

export function isBlockedIPv4(ip: string): boolean {
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

export function isBlockedIPv6(ip: string): boolean {
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

export function isBlockedHostnameLiteral(hostname: string): boolean {
    const lower = hostname.toLowerCase().replace(/^\[|\]$/g, '');
    if (BLOCKED_HOSTNAMES.has(lower)) return true;
    if (/^::1$/.test(lower) || /^::ffff:/.test(lower)) return true;
    return false;
}

export function isBlockedHostOrIp(hostnameOrIp: string): boolean {
    const normalized = hostnameOrIp.toLowerCase().replace(/^\[|\]$/g, '');
    if (isBlockedHostnameLiteral(normalized)) return true;
    if (/^\d{1,3}(\.\d{1,3}){3}$/.test(normalized)) {
        return isBlockedIPv4(normalized);
    }
    if (normalized.includes(':')) {
        return isBlockedIPv6(normalized);
    }
    return false;
}
