'use server';

import { auth } from '@/auth';
import { Octokit } from 'octokit';

export async function fetchUserPullRequests() {
    try {
        const session = await auth();
        if (!session?.user) {
            return { success: false, error: 'Unauthorized' };
        }

        const username = (session.user as any).username;
        const accessToken = (session as any).accessToken;

        if (!username || !accessToken) {
            return { success: false, error: 'Missing GitHub credentials' };
        }

        const octokit = new Octokit({ auth: accessToken });
        const owner = process.env.GITHUB_REGISTRY_OWNER || 'adriannoes';
        const repo = process.env.GITHUB_REGISTRY_REPO || 'asap-protocol';

        // Fetch open PRs created by the user targeting the registry
        const { data: prs } = await octokit.rest.pulls.list({
            owner,
            repo,
            state: 'open',
            sort: 'created',
            direction: 'desc',
        });

        // Filter PRs that are specifically from this user for Agent Registration
        const userRegistrationPrs = prs
            .filter(pr => pr.user?.login === username && pr.title.startsWith('Register Agent:'))
            .map(pr => ({
                id: pr.id,
                title: pr.title,
                url: pr.html_url,
                number: pr.number,
                state: pr.state, // 'open'
                createdAt: pr.created_at,
                // Simple heuristic for status. In a real app we'd check CI checks and review states.
                status: 'Pending Review',
            }));

        return { success: true, data: userRegistrationPrs };

    } catch (error) {
        console.error('Error fetching PRs:', error);
        return { success: false, error: 'Failed to fetch pull requests' };
    }
}
