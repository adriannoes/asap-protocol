/**
 * Builds GitHub Issue URLs for agent registration and verification (IssueOps flow).
 * Query parameter keys match the issue form template ids in register_agent.yml and request_verification.yml.
 */
import { z } from 'zod';
import type { ManifestFormValues } from './register-schema';

const REGISTER_TEMPLATE = 'register_agent.yml';
const VERIFY_TEMPLATE = 'request_verification.yml';

/**
 * Builds the new-issue URL with template and pre-filled query params.
 * User opens this in a new tab and clicks "Submit new issue" on GitHub.
 */
export function buildRegisterAgentIssueUrl(
    values: ManifestFormValues,
    options: { owner: string; repo: string }
): string {
    const { owner, repo } = options;
    const base = `https://github.com/${owner}/${repo}/issues/new`;
    const params = new URLSearchParams();

    params.set('template', REGISTER_TEMPLATE);
    params.set('title', `Register: ${values.name}`);

    params.set('name', values.name);
    params.set('description', values.description);
    params.set('manifest_url', values.manifest_url);
    params.set('http_endpoint', values.endpoint_http);
    params.set('websocket_endpoint', values.endpoint_ws ?? '');
    params.set('skills', values.skills);
    params.set('built_with', values.built_with ?? '');
    params.set('repository_url', values.repository_url ?? '');
    params.set('documentation_url', values.documentation_url ?? '');
    if (values.confirm) {
        params.set('confirm', '0');
    }

    const query = params.toString();
    return query ? `${base}?${query}` : base;
}

export const VerificationSchema = z.object({
    agent_id: z.string().min(1, 'Agent ID is required').max(200),
    why_verified: z.string().min(1, 'Please explain why this agent should be verified').max(2000),
    running_since: z.string().min(1, 'Please indicate how long the agent has been running').max(100),
    evidence: z.string().max(2000).optional(),
    contact: z.string().max(200).optional(),
});

export type VerificationFormValues = z.infer<typeof VerificationSchema>;

/**
 * Builds the new-issue URL for verification requests (template request_verification.yml).
 * Query param keys match the template body field ids.
 */
export function buildVerificationRequestIssueUrl(
    values: VerificationFormValues,
    options: { owner: string; repo: string }
): string {
    const { owner, repo } = options;
    const base = `https://github.com/${owner}/${repo}/issues/new`;
    const params = new URLSearchParams();

    params.set('template', VERIFY_TEMPLATE);
    params.set('title', `Verify: ${values.agent_id}`);

    params.set('agent_id', values.agent_id);
    params.set('why_verified', values.why_verified);
    params.set('running_since', values.running_since);
    if (values.evidence) params.set('evidence', values.evidence);
    if (values.contact) params.set('contact', values.contact);

    const query = params.toString();
    return query ? `${base}?${query}` : base;
}
