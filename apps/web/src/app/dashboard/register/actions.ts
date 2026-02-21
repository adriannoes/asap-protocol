'use server';

import { auth } from '@/auth';
import { ManifestSchema } from '@/lib/register-schema';
import { buildRegisterAgentIssueUrl } from '@/lib/github-issues';
import { isAllowedExternalUrl } from '@/lib/url-validator';
import { checkRateLimit } from '@/lib/rate-limit';

const DEFAULT_OWNER = 'adriannoes';
const DEFAULT_REPO = 'asap-protocol';

export async function submitAgentRegistration(values: unknown) {
    try {
        const session = await auth();
        if (!session?.user) {
            return { success: false, error: 'You must be logged in to register an agent.' };
        }

        const username = session.user.username;
        const userId = (session.user as { id?: string }).id ?? username ?? 'anonymous';

        if (!username) {
            return { success: false, error: 'GitHub account link missing or invalid. Please re-login.' };
        }

        if (!checkRateLimit(userId, 5, 60_000)) {
            return { success: false, error: 'Too many registration attempts. Please try again in a minute.' };
        }

        const parsed = ManifestSchema.safeParse(values);
        if (!parsed.success) {
            return { success: false, error: 'Invalid form data provided.' };
        }

        const data = parsed.data;
        const { manifest_url, endpoint_http, endpoint_ws } = data;

        const manifestCheck = isAllowedExternalUrl(manifest_url);
        if (!manifestCheck.valid) {
            return { success: false, error: `Manifest URL: ${manifestCheck.error}` };
        }
        const endpointCheck = isAllowedExternalUrl(endpoint_http);
        if (!endpointCheck.valid) {
            return { success: false, error: `Endpoint URL: ${endpointCheck.error}` };
        }
        if (endpoint_ws) {
            const wsCheck = isAllowedExternalUrl(endpoint_ws);
            if (!wsCheck.valid) {
                return { success: false, error: `WebSocket URL: ${wsCheck.error}` };
            }
        }

        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 3000);
            const manifestFetch = await fetch(manifest_url, {
                method: 'HEAD',
                signal: controller.signal,
            });
            clearTimeout(timeoutId);
            if (!manifestFetch.ok) {
                return { success: false, error: `Manifest URL returned status ${manifestFetch.status}. Must be reachable.` };
            }
        } catch (e: unknown) {
            const err = e as Error;
            return { success: false, error: `Could not reach Manifest URL: ${err?.message ?? manifest_url}` };
        }

        const owner = process.env.GITHUB_REGISTRY_OWNER || DEFAULT_OWNER;
        const repo = process.env.GITHUB_REGISTRY_REPO || DEFAULT_REPO;
        const issueUrl = buildRegisterAgentIssueUrl(data, { owner, repo });

        return { success: true, issueUrl };
    } catch (e) {
        console.error('Registration block error:', e);
        return { success: false, error: 'Internal server error processing registration.' };
    }
}
