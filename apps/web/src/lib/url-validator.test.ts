import { describe, it, expect } from 'vitest';
import { isAllowedExternalUrl } from './url-validator';

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
