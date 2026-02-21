'use server';

import { auth } from '@/auth';
import { buildVerificationRequestIssueUrl, type VerificationFormValues } from '@/lib/github-issues';

export async function submitVerificationRequest(
    values: VerificationFormValues
): Promise<{ success: boolean; issueUrl?: string; error?: string }> {
    try {
        const session = await auth();
        if (!session?.user) {
            return { success: false, error: 'Unauthorized' };
        }

        const owner = process.env.GITHUB_REGISTRY_OWNER || 'adriannoes';
        const repo = process.env.GITHUB_REGISTRY_REPO || 'asap-protocol';

        const issueUrl = buildVerificationRequestIssueUrl(values, { owner, repo });
        return { success: true, issueUrl };
    } catch (error) {
        console.error('Verification request URL build failed:', error);
        return { success: false, error: 'Failed to build verification issue URL.' };
    }
}
