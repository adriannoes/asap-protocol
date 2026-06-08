import { z } from 'zod';

const UrlQuerySchema = z
    .object({
        url: z.string().min(1).max(2048),
    })
    .strict();

export const HealthCheckQuerySchema = UrlQuerySchema;
export const ProxyCheckQuerySchema = UrlQuerySchema;

export const FixtureRegistryQuerySchema = z
    .object({
        count: z.coerce.number().int().min(1).max(2000).default(500),
    })
    .strict();

export const TestLoginQuerySchema = z
    .object({
        username: z.string().max(64).optional(),
        redirect: z.string().max(512).default('/dashboard'),
        id: z.string().max(128).optional(),
    })
    .strict();

export function parseSearchParams<T>(
    schema: z.ZodType<T>,
    searchParams: URLSearchParams
): { success: true; data: T } | { success: false; error: string } {
    const raw = Object.fromEntries(searchParams.entries());
    const parsed = schema.safeParse(raw);
    if (!parsed.success) {
        return { success: false, error: 'Invalid input' };
    }
    return { success: true, data: parsed.data };
}
