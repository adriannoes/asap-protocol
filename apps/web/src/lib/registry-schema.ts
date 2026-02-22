/**
 * Zod schema for runtime validation of registry.json response.
 * Prevents type assertion bypass (IMP-4).
 */
import { z } from 'zod';

const EndpointsSchema = z.record(z.string(), z.string());

const VerificationStatusSchema = z
    .object({
        status: z.string(),
        verified_at: z.string().optional(),
    })
    .optional()
    .nullable();

export const RegistryAgentSchema = z.object({
    id: z.string(),
    name: z.string(),
    description: z.string(),
    endpoints: EndpointsSchema,
    skills: z.array(z.string()).default([]),
    asap_version: z.string().optional(),
    repository_url: z.string().url().optional().nullable(),
    documentation_url: z.string().url().optional().nullable(),
    built_with: z.string().optional().nullable(),
    verification: VerificationStatusSchema,
}).passthrough();

export const RegistryResponseSchema = z.union([
    z.array(RegistryAgentSchema),
    z.object({ agents: z.array(RegistryAgentSchema) }),
]);

export type RegistryAgentValidated = z.infer<typeof RegistryAgentSchema>;
