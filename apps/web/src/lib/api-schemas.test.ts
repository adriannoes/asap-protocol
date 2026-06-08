import { describe, expect, it } from 'vitest';
import {
    FixtureRegistryQuerySchema,
    HealthCheckQuerySchema,
    ProxyCheckQuerySchema,
    TestLoginQuerySchema,
    parseSearchParams,
} from './api-schemas';

const STRICT_UNKNOWN_FIELD_CASES = [
    {
        schema: HealthCheckQuerySchema,
        valid: { url: 'https://example.com' },
        extra: { extra: 'x' },
    },
    {
        schema: ProxyCheckQuerySchema,
        valid: { url: 'https://example.com' },
        extra: { foo: 'bar' },
    },
    {
        schema: FixtureRegistryQuerySchema,
        valid: { count: '10' },
        extra: { unknown: '1' },
    },
    {
        schema: TestLoginQuerySchema,
        valid: { redirect: '/dashboard' },
        extra: { evil: '1' },
    },
] as const;

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

    it.each(STRICT_UNKNOWN_FIELD_CASES)('rejects unknown query fields', ({ schema, valid, extra }) => {
        const parsed = schema.safeParse({ ...valid, ...extra });
        expect(parsed.success).toBe(false);
        if (parsed.success) {
            return;
        }
        expect(parsed.error.issues[0]?.code).toBe('unrecognized_keys');
    });
});
