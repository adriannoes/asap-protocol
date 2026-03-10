'use server';

import { auth } from '@/auth';
import {
    buildVerificationRequestIssueUrl,
    VerificationSchema,
} from '@/lib/github-issues';
import { checkRateLimit } from '@/lib/rate-limit';

export async function submitVerificationRequest(
    values: unknown
): Promise<{ success: boolean; issueUrl?: string; error?: string }> {
    const session = await auth();
    if (!session?.user) {
        return { success: false, error: 'Unauthorized' };
    }

    const userId = (session.user as { id?: string }).id ?? 'anonymous';
    // Assuming 'username' is the appropriate field for username in session.user based on register/actions.ts
    const username = (session.user as any).username || session.user.name;
    const isE2E = process.env.ENABLE_FIXTURE_ROUTES === 'true' && username === 'e2e-tester';
    if (!isE2E && !checkRateLimit(userId, 5, 60_000)) {
        return { success: false, error: 'Too many verification attempts. Please try again in a minute.' };
    }

    const parsed = VerificationSchema.safeParse(values);
    if (!parsed.success) {
        return { success: false, error: 'Invalid form data.' };
    }

    const data = parsed.data;
    const owner = process.env.GITHUB_REGISTRY_OWNER || 'adriannoes';
    const repo = process.env.GITHUB_REGISTRY_REPO || 'asap-protocol';

    try {
        const issueUrl = buildVerificationRequestIssueUrl(data, { owner, repo });
        return { success: true, issueUrl };
    } catch (error) {
        console.error('Verification request URL build failed:', error);
        return { success: false, error: 'Failed to build verification issue URL.' };
    }
}
