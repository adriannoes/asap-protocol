import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import * as nodeDns from 'node:dns';
import { isAllowedExternalUrl, isAllowedProxyUrl } from './url-validator';
import { isAllowedProxyUrlAsync } from './url-validator-server';

describe('isAllowedExternalUrl', () => {
    it('allows valid public HTTPS URL', () => {
        expect(isAllowedExternalUrl('https://example.com/manifest')).toEqual({ valid: true });
        expect(isAllowedExternalUrl('https://api.myagent.io')).toEqual({ valid: true });
    });

    it('allows valid public HTTP URL', () => {
        expect(isAllowedExternalUrl('http://example.com')).toEqual({ valid: true });
    });

    it('rejects localhost', () => {
        expect(isAllowedExternalUrl('http://localhost:8080').valid).toBe(false);
        expect(isAllowedExternalUrl('https://localhost/manifest').valid).toBe(false);
    });

    it('rejects 127.0.0.1', () => {
        expect(isAllowedExternalUrl('http://127.0.0.1:3000').valid).toBe(false);
    });

    it('rejects 0.0.0.0', () => {
        expect(isAllowedExternalUrl('http://0.0.0.0:8080').valid).toBe(false);
    });

    it('rejects IPv6 loopback ::1', () => {
        expect(isAllowedExternalUrl('http://[::1]/manifest').valid).toBe(false);
    });

    it('rejects IPv6-mapped 127.0.0.1', () => {
        expect(isAllowedExternalUrl('http://[::ffff:127.0.0.1]/manifest').valid).toBe(false);
    });

    it('rejects cloud metadata hostnames', () => {
        expect(isAllowedExternalUrl('http://metadata.google.internal/computeMetadata/v1/').valid).toBe(false);
        expect(isAllowedExternalUrl('http://metadata.aws.internal/').valid).toBe(false);
        expect(isAllowedExternalUrl('http://169.254.169.254/latest/meta-data').valid).toBe(false);
    });

    it('rejects private IPv4 ranges', () => {
        expect(isAllowedExternalUrl('http://192.168.1.1').valid).toBe(false);
        expect(isAllowedExternalUrl('http://10.0.0.1').valid).toBe(false);
        expect(isAllowedExternalUrl('http://172.16.0.1').valid).toBe(false);
        expect(isAllowedExternalUrl('http://172.31.255.255').valid).toBe(false);
    });

    it('rejects non-HTTP(S) protocols', () => {
        expect(isAllowedExternalUrl('file:///etc/passwd').valid).toBe(false);
        expect(isAllowedExternalUrl('ftp://example.com').valid).toBe(false);
    });

    it('returns error message for invalid URL', () => {
        const result = isAllowedExternalUrl('not-a-url');
        expect(result.valid).toBe(false);
        expect(result.error).toBeDefined();
    });

    it('returns error message for blocked host', () => {
        const result = isAllowedExternalUrl('http://localhost');
        expect(result.valid).toBe(false);
        expect(result.error).toContain('Internal/Private');
    });
});

describe('isAllowedProxyUrl', () => {
    it('allows valid public HTTPS URL', () => {
        expect(isAllowedProxyUrl('https://example.com/health')).toEqual({ valid: true });
        expect(isAllowedProxyUrl('https://api.myagent.io')).toEqual({ valid: true });
    });

    it('rejects HTTP (HTTPS only)', () => {
        expect(isAllowedProxyUrl('http://example.com').valid).toBe(false);
        expect(isAllowedProxyUrl('http://example.com/health').valid).toBe(false);
    });

    it('rejects localhost and private IPs', () => {
        expect(isAllowedProxyUrl('https://localhost').valid).toBe(false);
        expect(isAllowedProxyUrl('https://127.0.0.1').valid).toBe(false);
        expect(isAllowedProxyUrl('https://192.168.1.1').valid).toBe(false);
        expect(isAllowedProxyUrl('https://10.0.0.1').valid).toBe(false);
    });

    it('rejects non-HTTP(S) protocols', () => {
        expect(isAllowedProxyUrl('file:///etc/passwd').valid).toBe(false);
    });
});

describe('isAllowedProxyUrlAsync (DNS rebinding mitigation)', () => {
    let resolve4Spy: ReturnType<typeof vi.spyOn>;
    let resolve6Spy: ReturnType<typeof vi.spyOn>;

    beforeEach(() => {
        resolve4Spy = vi.spyOn(nodeDns.promises, 'resolve4').mockRejectedValue(new Error('ENOTFOUND'));
        resolve6Spy = vi.spyOn(nodeDns.promises, 'resolve6').mockRejectedValue(new Error('ENOTFOUND'));
    });

    afterEach(() => {
        resolve4Spy?.mockRestore();
        resolve6Spy?.mockRestore();
    });

    it('rejects when hostname resolves to private IPv4', async () => {
        resolve4Spy.mockResolvedValue(['192.168.1.1']);
        resolve6Spy.mockResolvedValue([]);
        const result = await isAllowedProxyUrlAsync('https://attacker.example.com/health');
        expect(result.valid).toBe(false);
        expect(result.error).toContain('Private');
    });

    it('rejects when hostname resolves to loopback', async () => {
        resolve4Spy.mockResolvedValue(['127.0.0.1']);
        resolve6Spy.mockResolvedValue([]);
        const result = await isAllowedProxyUrlAsync('https://evil.example.com/');
        expect(result.valid).toBe(false);
    });

    it('rejects when hostname resolves to link-local (169.254.x.x)', async () => {
        resolve4Spy.mockResolvedValue(['169.254.169.254']);
        resolve6Spy.mockResolvedValue([]);
        const result = await isAllowedProxyUrlAsync('https://metadata-bypass.example.com/');
        expect(result.valid).toBe(false);
    });

    it('allows when hostname resolves to public IPv4 only', async () => {
        resolve4Spy.mockResolvedValue(['93.184.216.34']);
        resolve6Spy.mockResolvedValue([]);
        const result = await isAllowedProxyUrlAsync('https://example.com/health');
        expect(result.valid).toBe(true);
    });

    it('rejects when any of multiple resolved IPs is private', async () => {
        resolve4Spy.mockResolvedValue(['93.184.216.34', '192.168.1.1']);
        resolve6Spy.mockResolvedValue([]);
        const result = await isAllowedProxyUrlAsync('https://dual-stack.example.com/');
        expect(result.valid).toBe(false);
    });

    it('rejects when DNS resolution fails for both A and AAAA', async () => {
        resolve4Spy.mockRejectedValue(new Error('ENOTFOUND'));
        resolve6Spy.mockRejectedValue(new Error('ENOTFOUND'));
        const result = await isAllowedProxyUrlAsync('https://nonexistent.invalid/');
        expect(result.valid).toBe(false);
        expect(result.error).toContain('resolve');
    });
});
