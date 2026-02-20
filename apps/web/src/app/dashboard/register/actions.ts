'use server';

import { auth, decryptToken } from '@/auth';
import { z } from 'zod';
import { Octokit } from 'octokit';
import type { Manifest, Skill } from '@/types/protocol';
import { isAllowedExternalUrl } from '@/lib/url-validator';
import { checkRateLimit } from '@/lib/rate-limit';

// Match the client schema
const formSchema = z.object({
    name: z.string().min(3).max(50).regex(/^[a-z0-9-]+$/),
    description: z.string().min(10).max(200),
    manifest_url: z.string().url(),
    endpoint_http: z.string().url(),
    endpoint_ws: z.string().url().optional().or(z.literal('')),
    skills: z.string().min(1),
});

export async function submitAgentRegistration(values: z.infer<typeof formSchema>) {
    try {
        const session = await auth();
        if (!session?.user) {
            return { success: false, error: 'You must be logged in to register an agent.' };
        }

        const username = session.user.username;
        const encryptedAccessToken = session.encryptedAccessToken;
        const userId = (session.user as { id?: string }).id ?? username ?? 'anonymous';

        if (!username || !encryptedAccessToken) {
            return { success: false, error: 'GitHub account link missing or invalid. Please re-login.' };
        }

        if (!checkRateLimit(userId, 5, 60_000)) {
            return { success: false, error: 'Too many registration attempts. Please try again in a minute.' };
        }

        const accessToken = await decryptToken(encryptedAccessToken);

        const parsed = formSchema.safeParse(values);
        if (!parsed.success) {
            return { success: false, error: 'Invalid form data provided.' };
        }

        const { name, description, manifest_url, endpoint_http, endpoint_ws, skills } = parsed.data;

        const agentId = `urn:asap:agent:${username}:${name}`;

        const skillsList: Skill[] = skills.split(',').map(s => s.trim()).filter(Boolean).map(s => ({
            id: s,
            description: `Capability: ${s}`,
        }));

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

        const octokit = new Octokit({ auth: accessToken });
        const owner = process.env.GITHUB_REGISTRY_OWNER || 'adriannoes';
        const repo = process.env.GITHUB_REGISTRY_REPO || 'asap-protocol';
        const targetBranch = `register/${username}-${name}-${Date.now()}`;
        const registryPath = 'registry.json';

        try {
            let currentRegistry: Manifest[] = [];
            try {
                const { data: fileData } = await octokit.rest.repos.getContent({
                    owner,
                    repo,
                    path: registryPath,
                    ref: 'main',
                });
                if (!Array.isArray(fileData) && fileData.type === 'file' && fileData.content) {
                    const contentStr = Buffer.from(fileData.content, 'base64').toString('utf-8');
                    currentRegistry = JSON.parse(contentStr);
                }
            } catch (e) {
                console.log('registry.json not found or error parsing, starting fresh.', e);
            }

            const { data: fork } = await octokit.rest.repos.createFork({ owner, repo });
            await new Promise(resolve => setTimeout(resolve, 3000));

            const defaultBranch = fork.default_branch || 'main';
            const { data: refData } = await octokit.rest.git.getRef({
                owner: fork.owner.login,
                repo: fork.name,
                ref: `heads/${defaultBranch}`,
            });
            await octokit.rest.git.createRef({
                owner: fork.owner.login,
                repo: fork.name,
                ref: `refs/heads/${targetBranch}`,
                sha: refData.object.sha,
            });

            let fileSha: string | undefined;
            try {
                const { data: fileData } = await octokit.rest.repos.getContent({
                    owner: fork.owner.login,
                    repo: fork.name,
                    path: registryPath,
                    ref: targetBranch,
                });
                if (!Array.isArray(fileData) && fileData.type === 'file' && fileData.sha) {
                    fileSha = fileData.sha;
                    const contentStr = Buffer.from(fileData.content, 'base64').toString('utf-8');
                    currentRegistry = JSON.parse(contentStr);
                }
            } catch (e) {
                if ((e as { status?: number })?.status !== 404) {
                    console.log('Error reading registry from fork branch', e);
                }
            }

            const newAgent: Omit<Manifest, 'ttl_seconds'> = {
                id: agentId,
                name: agentId.split(':').pop() ?? name,
                description,
                version: '1.0.0' as unknown as Manifest['version'],
                endpoints: {
                    asap: endpoint_http,
                    ...(endpoint_ws ? { events: endpoint_ws } : {}),
                },
                capabilities: {
                    asap_version: '0.1',
                    skills: skillsList,
                },
            };

            currentRegistry = currentRegistry.filter(a => a.id !== agentId);
            currentRegistry.push(newAgent as Manifest);
            const updatedContent = JSON.stringify(currentRegistry, null, 2);

            await octokit.rest.repos.createOrUpdateFileContents({
                owner: fork.owner.login,
                repo: fork.name,
                path: registryPath,
                message: `register: add agent ${agentId}`,
                content: Buffer.from(updatedContent).toString('base64'),
                branch: targetBranch,
                sha: fileSha,
            });

            const { data: prData } = await octokit.rest.pulls.create({
                owner,
                repo,
                title: `Register Agent: ${agentId}`,
                head: `${fork.owner.login}:${targetBranch}`,
                base: 'main',
                body: `Automated agent registration via Developer Dashboard.\n\n**Agent ID:** \`${agentId}\`\n**Submitted By:** @${username}\n**Manifest:** ${manifest_url}`,
            });

            return { success: true, prUrl: prData.html_url };
        } catch (octoError: unknown) {
            const err = octoError as Error;
            console.error('GitHub API Error', err);
            return {
                success: false,
                error: `Failed to create GitHub Pull Request: ${err.message || 'Unknown error'}`,
            };
        }
    } catch (e) {
        console.error('Registration block error:', e);
        return { success: false, error: 'Internal server error processing registration.' };
    }
}
