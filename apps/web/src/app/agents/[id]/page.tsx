import { Metadata } from 'next';
import { fetchAgentById, fetchRegistry, fetchRevokedUrns } from '@/lib/registry';
import { notFound } from 'next/navigation';
import { AgentDetailClient } from './agent-detail-client';

export const revalidate = 60;

type Props = {
    params: Promise<{ id: string }>;
};

export async function generateStaticParams() {
    const agents = await fetchRegistry();
    return agents.map((agent) => ({
        id: encodeURIComponent(agent.id ?? ''),
    }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
    const p = await params;
    const decodedId = decodeURIComponent(p.id);
    const agent = await fetchAgentById(decodedId);

    if (!agent) {
        return {
            title: 'Agent Not Found | ASAP Protocol',
        };
    }

    return {
        title: `${agent.name} | ASAP Protocol Registry`,
        description: agent.description ?? '',
        openGraph: {
            title: `${agent.name} | ASAP Protocol Registry`,
            description: agent.description ?? '',
            type: 'website',
        },
        twitter: {
            card: 'summary_large_image',
            title: `${agent.name} | ASAP Protocol Registry`,
            description: agent.description ?? '',
        },
    };
}

export default async function AgentDetailPage({ params }: Props) {
    const p = await params;
    const decodedId = decodeURIComponent(p.id);

    const [agent, revokedUrns] = await Promise.all([
        fetchAgentById(decodedId),
        fetchRevokedUrns(),
    ]);

    if (!agent) {
        return notFound();
    }

    const isRevoked = revokedUrns.has(agent.id || '');

    return (
        <div className="container mx-auto py-10 px-4 max-w-5xl">
            <AgentDetailClient agent={agent} isRevoked={isRevoked} />
        </div>
    );
}
