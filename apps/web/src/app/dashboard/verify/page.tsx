import { Metadata } from 'next';
import { auth } from '@/auth';
import { redirect } from 'next/navigation';
import { VerifyForm } from './verify-form';

export const metadata: Metadata = {
    title: 'Request Verification | Developer Dashboard',
    description: 'Request the Verified badge for an ASAP agent already listed in the registry.',
};

type PageProps = {
    searchParams: Promise<{ agent_id?: string }>;
};

export default async function VerifyPage({ searchParams }: PageProps) {
    const session = await auth();

    if (!session?.user) {
        redirect('/');
    }

    const params = await searchParams;
    const agentId = typeof params.agent_id === 'string' ? params.agent_id.trim() : '';

    return (
        <div className="container mx-auto py-10 px-4 max-w-3xl">
            <div className="mb-8 border-b pb-6">
                <h1 className="text-3xl font-bold tracking-tight">Request Verified Badge</h1>
                <p className="text-muted-foreground mt-2">
                    Request the <strong>Verified</strong> badge for an agent already in the registry. You will be taken to GitHub to submit
                    a pre-filled issue; maintainers will review your request and update the registry manually.
                </p>
            </div>

            {!agentId ? (
                <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4 text-sm text-amber-700 dark:text-amber-400">
                    <p>No agent selected. Open this page from the dashboard by clicking &quot;Apply for Verified&quot; on a listed agent card, or add <code className="rounded bg-muted px-1">?agent_id=urn:asap:agent:username:name</code> to the URL.</p>
                    <a href="/dashboard" className="mt-2 inline-block font-medium underline">Return to Dashboard</a>
                </div>
            ) : (
                <VerifyForm defaultAgentId={agentId} />
            )}
        </div>
    );
}
