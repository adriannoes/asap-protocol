/**
 * Shared Zod schema for agent registration form and server action.
 * Matches GitHub Issue Template (register_agent.yml) and RegistryEntry fields.
 * Used for client-side validation and server-side parsing.
 *
 * Required: name, description, manifest_url, endpoint_http, skills, confirm.
 * Optional: endpoint_ws, built_with, repository_url, documentation_url.
 */
import { z } from 'zod';

export const ManifestSchema = z.object({
    name: z
        .string()
        .min(3)
        .max(50)
        .regex(/^[a-z0-9-]+$/, {
            message:
                'Name can only contain lowercase letters, numbers, and hyphens (slug-friendly).',
        }),
    description: z.string().min(10).max(200),
    manifest_url: z.string().url({
        message: 'Must be a valid URL starting with http:// or https://',
    }),
    endpoint_http: z.string().url({ message: 'Must be a valid URL' }),
    endpoint_ws: z.string().url().optional().or(z.literal('')),
    skills: z.string().min(1, { message: 'At least one skill is required' }),
    built_with: z.string().optional(),
    repository_url: z.string().url().optional().or(z.literal('')),
    documentation_url: z.string().url().optional().or(z.literal('')),
    confirm: z.boolean().refine((v) => v === true, {
        message: 'You must confirm before submitting.',
    }),
});

export type ManifestFormValues = z.infer<typeof ManifestSchema>;
