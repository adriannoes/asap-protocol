'use server';

import { auth } from '@/auth';
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

        const username = (session.user as any).username;
        const accessToken = (session as any).accessToken; // Requires adding accessToken to session via auth.ts callbacks

        if (!username || !accessToken) {
            return { success: false, error: 'GitHub account link missing or invalid. Please re-login.' };
        }

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
        // In a strict implementation, we would verify Ed25519 signatures here.
        try {
            const manifestCheck = await fetch(manifest_url, { method: 'HEAD' });
            if (!manifestCheck.ok) {
                return { success: false, error: `Manifest URL returned status ${manifestCheck.status}. Must be reachable.` };
            }
        } catch (e) {
            return { success: false, error: `Could not reach Manifest URL: ${manifest_url}` };
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
            let registryPath = 'registry.json';
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
                version: "1.0.0" as any, // Type coercion to satisfy generated interface
                endpoints: {
                    asap: endpoint_http,
                    ...(endpoint_ws ? { events: endpoint_ws } : {})
                },
                capabilities: {
                    asap_version: "0.1",
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

        } catch (octoError: any) {
            console.error("GitHub API Error", octoError);
            return {
                success: false,
                error: `Failed to create GitHub Pull Request: ${octoError.message || 'Unknown error'}`
            };
        }

    } catch (e) {
        console.error('Registration block error:', e);
        return { success: false, error: 'Internal server error processing registration.' };
    }
}
