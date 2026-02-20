import { Metadata } from 'next';
import { fetchAgentById, fetchRegistry } from '@/lib/registry';
import { notFound } from 'next/navigation';
import { AgentDetailClient } from './agent-detail-client';

export const revalidate = 60; // ISR

type Props = {
    params: Promise<{ id: string }>;
};

// Generate static params for existing agents in registry
export async function generateStaticParams() {
    const agents = await fetchRegistry();
    return agents.map((agent) => ({
        id: encodeURIComponent(agent.id as string),
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
        description: agent.description as string,
    };
}

export default async function AgentDetailPage({ params }: Props) {
    const p = await params;
    const decodedId = decodeURIComponent(p.id);
    const agent = await fetchAgentById(decodedId);

    if (!agent) {
        notFound();
    }

    return (
        <div className="container mx-auto py-10 px-4 max-w-5xl">
            <AgentDetailClient agent={agent} />
        </div>
    );
}
