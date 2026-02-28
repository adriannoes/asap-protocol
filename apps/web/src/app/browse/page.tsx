import { Metadata } from 'next';
import { fetchRegistry, fetchRevokedUrns } from '@/lib/registry';
import { BrowseContent } from './browse-content';

export const metadata: Metadata = {
    title: 'Browse Agents | ASAP Protocol Marketplace',
    description: 'Discover and integrate autonomous AI agents from the ASAP Protocol registry.',
};

/** Must be static for Next.js segment config. Fetch uses REGISTRY_REVALIDATE_SECONDS from registry.ts. */
export const revalidate = 60;

export default async function BrowsePage() {
    const allAgents = await fetchRegistry();
    const revokedUrns = await fetchRevokedUrns();
    const activeAgents = allAgents.filter((agent) => !revokedUrns.has(agent.id || ''));

    return (
        <div className="container mx-auto py-10 px-4 max-w-7xl">
            <div className="flex flex-col space-y-6">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Agent Registry</h1>
                    <p className="text-muted-foreground mt-2">
                        Browse and connect with verified autonomous agents. Currently tracking {activeAgents.length} agents.
                    </p>
                </div>

                <BrowseContent initialAgents={activeAgents} />
            </div>
        </div>
    );
}
