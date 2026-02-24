'use server';

import { unstable_cache, updateTag } from 'next/cache';
import { auth, decryptToken } from '@/auth';
import { Octokit } from 'octokit';
import { checkRateLimit } from '@/lib/rate-limit';

const CACHE_TTL_SECONDS = 30;
const CACHE_TAG_PREFIX = 'user-registration-issues';

async function fetchIssuesFromGitHub(
    accessToken: string,
    username: string,
    owner: string,
    repo: string
) {
    const octokit = new Octokit({ auth: accessToken });
    const response = await octokit.rest.issues.listForRepo({
        owner,
        repo,
        state: 'open',
        labels: 'registration',
        sort: 'created',
        direction: 'desc',
    });
    const rateLimitRemaining = response.headers['x-ratelimit-remaining'];
    if (rateLimitRemaining !== undefined) {
        console.info(
            JSON.stringify({
                event: 'github.api.rate_limit',
                x_ratelimit_remaining: rateLimitRemaining,
                endpoint: 'issues.listForRepo',
            })
        );
    }
    const issues = response.data;
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
    return { success: true as const, data: userRegistrationIssues };
}

export async function revalidateUserRegistrationIssues() {
    const session = await auth();
    if (!session?.user) return;
    const userId =
        (session.user as { id?: string }).id ?? session.user.username ?? 'anonymous';
    updateTag(`${CACHE_TAG_PREFIX}-${userId}`);
}

export async function fetchUserRegistrationIssues() {
    try {
        const session = await auth();
        if (!session?.user) {
            return { success: false, error: 'Unauthorized' };
        }

        const userId =
            (session.user as { id?: string }).id ?? session.user.username ?? 'anonymous';
        if (!checkRateLimit(userId, 30, 60_000)) {
            return { success: false, error: 'Too many requests. Please try again in a minute.' };
        }

        const username = session.user.username;
        const encryptedAccessToken = session.encryptedAccessToken;

        if (!username || !encryptedAccessToken) {
            return { success: false, error: 'Missing GitHub credentials' };
        }

        const accessToken = await decryptToken(encryptedAccessToken);
        const owner = process.env.GITHUB_REGISTRY_OWNER || 'adriannoes';
        const repo = process.env.GITHUB_REGISTRY_REPO || 'asap-protocol';

        const cacheTag = `${CACHE_TAG_PREFIX}-${userId}`;
        const getCached = unstable_cache(
            () => fetchIssuesFromGitHub(accessToken, username, owner, repo),
            [CACHE_TAG_PREFIX, userId, owner, repo],
            { tags: [cacheTag], revalidate: CACHE_TTL_SECONDS }
        );

        return await getCached();
    } catch (error) {
        console.error('Error fetching registration issues:', error);
        return { success: false, error: 'Failed to fetch registration issues' };
    }
}
