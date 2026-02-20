'use server';

import { auth, decryptToken } from '@/auth';
import { z } from 'zod';
import { Octokit } from 'octokit';
import { Manifest } from '@/types/protocol';

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

        if (!username || !encryptedAccessToken) {
            return { success: false, error: 'GitHub account link missing or invalid. Please re-login.' };
        }

        const accessToken = await decryptToken(encryptedAccessToken);

        // 1. Validate Form Data
        const parsed = formSchema.safeParse(values);
        if (!parsed.success) {
            return { success: false, error: 'Invalid form data provided.' };
        }

        const { name, description, manifest_url, endpoint_http, endpoint_ws, skills } = parsed.data;

        // Construct the Agent ID using the username as the namespace to prevent collisions
        const agentId = `urn:asap:agent:${username}:${name}`;

        // Split skills correctly
        const skillsList = skills.split(',').map(s => s.trim()).filter(Boolean).map(s => ({
            id: s,
            description: `Capability: ${s}`
        }));

        // 2. Fetch remote manifest to test reachability (Mocking full validation for M2 MVP)
        // SSRF Mitigation added to prevent scanning internal networks
        try {
            const parsedUrl = new URL(manifest_url);
            if (parsedUrl.protocol !== 'https:' && parsedUrl.protocol !== 'http:') {
                return { success: false, error: 'Manifest URL must use HTTP or HTTPS.' };
            }

            const hostname = parsedUrl.hostname.toLowerCase();
            const isLocalOrPrivate = hostname === 'localhost' ||
                hostname === '127.0.0.1' ||
                hostname === '::1' ||
                hostname.startsWith('192.168.') ||
                hostname.startsWith('10.') ||
                hostname.startsWith('169.254.') ||
                /^172\.(1[6-9]|2[0-9]|3[0-1])\./.test(hostname);

            if (isLocalOrPrivate) {
                return { success: false, error: 'Internal/Private network addresses are not allowed for manifests.' };
            }

            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 3000); // 3 seconds timeout

            const manifestCheck = await fetch(manifest_url, {
                method: 'HEAD',
                signal: controller.signal
            });
            clearTimeout(timeoutId);

            if (!manifestCheck.ok) {
                return { success: false, error: `Manifest URL returned status ${manifestCheck.status}. Must be reachable.` };
            }
        } catch (e: unknown) {
            const err = e as Error;
            return { success: false, error: `Could not reach Manifest URL: ${err?.message || manifest_url}` };
        }

        // 3. GitHub Automation via Octokit (Task 2.4.3)
        const octokit = new Octokit({ auth: accessToken });
        const owner = process.env.GITHUB_REGISTRY_OWNER || 'adriannoes';
        const repo = process.env.GITHUB_REGISTRY_REPO || 'asap-protocol';
        const targetBranch = `register/${username}-${name}-${Date.now()}`;

        try {
            // A. Get the SHA of the main branch to branch off from
            const { data: refData } = await octokit.rest.git.getRef({
                owner,
                repo,
                ref: 'heads/main',
            });
            const baseSha = refData.object.sha;

            // B. Create the new branch
            await octokit.rest.git.createRef({
                owner,
                repo,
                ref: `refs/heads/${targetBranch}`,
                sha: baseSha,
            });

            // C. Fetch existing registry.json
            const registryPath = 'registry.json';
            let fileSha: string | undefined;
            let currentRegistry: Manifest[] = [];

            try {
                const { data: fileData } = await octokit.rest.repos.getContent({
                    owner,
                    repo,
                    path: registryPath,
                    ref: targetBranch,
                });

                if (!Array.isArray(fileData) && fileData.type === 'file' && fileData.content) {
                    fileSha = fileData.sha;
                    const contentStr = Buffer.from(fileData.content, 'base64').toString('utf-8');
                    currentRegistry = JSON.parse(contentStr);
                }
            } catch (e) {
                console.log("registry.json not found or error parsing, starting fresh.", e);
            }

            // D. Append the new agent to the registry list
            const newAgent: Partial<Manifest> = {
                id: agentId,
                name: agentId.split(':').pop(), // Use slug name
                description: description,
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                version: "1.0.0" as any, // Type coercion to satisfy generated interface
                endpoints: {
                    asap: endpoint_http,
                    ...(endpoint_ws ? { events: endpoint_ws } : {})
                },
                capabilities: {
                    asap_version: "0.1",
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    skills: skillsList as any
                }
            };

            // Remove existing agent with same ID if it exists (update scenario)
            currentRegistry = currentRegistry.filter(a => a.id !== agentId);
            currentRegistry.push(newAgent as Manifest);

            const updatedContent = JSON.stringify(currentRegistry, null, 2);

            // E. Update the file on the new branch
            await octokit.rest.repos.createOrUpdateFileContents({
                owner,
                repo,
                path: registryPath,
                message: `register: add agent ${agentId}`,
                content: Buffer.from(updatedContent).toString('base64'),
                branch: targetBranch,
                sha: fileSha, // Required if updating
            });

            // F. Create the Pull Request
            const { data: prData } = await octokit.rest.pulls.create({
                owner,
                repo,
                title: `Register Agent: ${agentId}`,
                head: targetBranch,
                base: 'main',
                body: `Automated agent registration via Developer Dashboard.\n\n**Agent ID:** \`${agentId}\`\n**Submitted By:** @${username}\n**Manifest:** ${manifest_url}`,
            });

            return { success: true, prUrl: prData.html_url };

        } catch (octoError: unknown) {
            const err = octoError as Error;
            console.error("GitHub API Error", err);
            return {
                success: false,
                error: `Failed to create GitHub Pull Request: ${err.message || 'Unknown error'}`
            };
        }

    } catch (e) {
        console.error('Registration block error:', e);
        return { success: false, error: 'Internal server error processing registration.' };
    }
}
