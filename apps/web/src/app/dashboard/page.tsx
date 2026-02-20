import { Metadata } from 'next';
import { auth } from '@/auth';
import { redirect } from 'next/navigation';
import { DashboardClient } from './dashboard-client';
import { fetchRegistry } from '@/lib/registry';

export const metadata: Metadata = {
    title: 'Developer Dashboard | ASAP Protocol',
    description: 'Manage your autonomous agents, monitor usage, and configure API keys.',
};

export default async function DashboardPage() {
    const session = await auth();

    if (!session?.user) {
        redirect('/');
    }

    const username = session.user.username || '';

    // Ownership: strict URN prefix urn:asap:agent:<username>: to avoid false positives.
    const allAgents = await fetchRegistry();
    const prefix = username ? `urn:asap:agent:${username.toLowerCase()}:` : '';
    const myAgents = prefix ? allAgents.filter(a => (a.id ?? '').toLowerCase().startsWith(prefix)) : [];

    return (
        <div className="container mx-auto py-10 px-4 max-w-6xl">
            <div className="mb-8">
                <h1 className="text-3xl font-bold tracking-tight">Developer Dashboard</h1>
                <p className="text-muted-foreground mt-2">
                    Manage your agents, monitor performance, and configure integrations.
                </p>
            </div>

            <DashboardClient initialAgents={myAgents} username={username} />
        </div>
    );
}
