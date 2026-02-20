import { Metadata } from 'next';
import { fetchRegistry } from '@/lib/registry';
import { BrowseContent } from './browse-content';

export const metadata: Metadata = {
    title: 'Browse Agents | ASAP Protocol Marketplace',
    description: 'Discover and integrate autonomous AI agents from the ASAP Protocol registry.',
};

// Next.js 15 route segment config for ISR
export const revalidate = 60;

export default async function BrowsePage() {
    const agents = await fetchRegistry();

    return (
        <div className="container mx-auto py-10 px-4 max-w-7xl">
            <div className="flex flex-col space-y-6">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Agent Registry</h1>
                    <p className="text-muted-foreground mt-2">
                        Browse and connect with verified autonomous agents. Currently tracking {agents.length} agents.
                    </p>
                </div>

                <BrowseContent initialAgents={agents} />
            </div>
        </div>
    );
}
