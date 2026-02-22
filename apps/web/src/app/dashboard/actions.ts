'use server';

import { auth, decryptToken } from '@/auth';
import { Octokit } from 'octokit';
import { checkRateLimit } from '@/lib/rate-limit';

export async function fetchUserRegistrationIssues() {
    try {
        const session = await auth();
        if (!session?.user) {
            return { success: false, error: 'Unauthorized' };
        }

        const userId = (session.user as { id?: string }).id ?? session.user.username ?? 'anonymous';
        if (!checkRateLimit(userId, 30, 60_000)) {
            return { success: false, error: 'Too many requests. Please try again in a minute.' };
        }

        const username = session.user.username;
        const encryptedAccessToken = session.encryptedAccessToken;

        if (!username || !encryptedAccessToken) {
            return { success: false, error: 'Missing GitHub credentials' };
        }

        const accessToken = await decryptToken(encryptedAccessToken);

        const octokit = new Octokit({ auth: accessToken });
        const owner = process.env.GITHUB_REGISTRY_OWNER || 'adriannoes';
        const repo = process.env.GITHUB_REGISTRY_REPO || 'asap-protocol';

        // Fetch open issues with label "registration" (IssueOps flow)
        const { data: issues } = await octokit.rest.issues.listForRepo({
            owner,
            repo,
            state: 'open',
            labels: 'registration',
            sort: 'created',
            direction: 'desc',
        });

        // Only issues (not PRs), created by this user
        const userRegistrationIssues = issues
            .filter((issue) => !issue.pull_request && issue.user?.login === username)
            .map((issue) => ({
                id: issue.id,
                number: issue.number,
                title: issue.title,
                url: issue.html_url ?? '',
                state: issue.state,
                status: 'Pending',
            }));

        return { success: true, data: userRegistrationIssues };
    } catch (error) {
        console.error('Error fetching registration issues:', error);
        return { success: false, error: 'Failed to fetch registration issues' };
    }
}
