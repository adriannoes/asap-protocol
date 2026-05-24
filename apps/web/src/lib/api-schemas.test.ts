import { describe, expect, it } from 'vitest';
import {
    FixtureRegistryQuerySchema,
    HealthCheckQuerySchema,
    ProxyCheckQuerySchema,
    TestLoginQuerySchema,
    parseSearchParams,
} from './api-schemas';

describe('api-schemas', () => {
    it('HealthCheckQuerySchema requires url', () => {
        expect(HealthCheckQuerySchema.safeParse({}).success).toBe(false);
        expect(HealthCheckQuerySchema.safeParse({ url: 'https://example.com' }).success).toBe(true);
    });

    it('ProxyCheckQuerySchema rejects empty url', () => {
        expect(ProxyCheckQuerySchema.safeParse({ url: '' }).success).toBe(false);
    });

    it('FixtureRegistryQuerySchema coerces and clamps count', () => {
        expect(FixtureRegistryQuerySchema.parse({ count: '10' }).count).toBe(10);
        expect(FixtureRegistryQuerySchema.parse({}).count).toBe(500);
        expect(FixtureRegistryQuerySchema.safeParse({ count: '0' }).success).toBe(false);
        expect(FixtureRegistryQuerySchema.safeParse({ count: '99999' }).success).toBe(false);
        expect(FixtureRegistryQuerySchema.safeParse({ count: 'abc' }).success).toBe(false);
    });

    it('TestLoginQuerySchema applies defaults', () => {
        const parsed = TestLoginQuerySchema.parse({});
        expect(parsed.redirect).toBe('/dashboard');
        expect(parsed.username).toBeUndefined();
    });

    it('parseSearchParams returns error for invalid input', () => {
        const params = new URLSearchParams('count=abc');
        const result = parseSearchParams(FixtureRegistryQuerySchema, params);
        expect(result.success).toBe(false);
        if (!result.success) {
            expect(result.error).toBe('Invalid input');
        }
    });
});
