import Link from 'next/link';
import type { Metadata } from 'next';
import type { LucideIcon } from 'lucide-react';
import { ArrowLeft, Database, ShieldCheck, Zap, Activity, Globe, Lock, Code } from 'lucide-react';
import { notFound } from 'next/navigation';
import { BentoGrid, BentoCard } from '@/components/ui/bento-grid';

export function generateStaticParams() {
    return [
        { slug: 'lite-registry' },
        { slug: 'verified-trust' },
        { slug: '1-click-integration' },
        { slug: 'full-observability' },
    ];
}

type FeatureCapability = { title: string; description: string; icon: LucideIcon };

const FEATURE_CONTENT: Record<
    string,
    {
        title: string;
        description: string;
        icon: React.ElementType;
        content: React.ReactNode;
        capabilities: FeatureCapability[];
    }
> = {
    'lite-registry': {
        title: 'Lite Registry',
        description: 'Zero database overhead. Pure speed and resilience.',
        icon: Database,
        capabilities: [
            { title: 'CDN-Optimized', description: 'Delivered instantaneously across global Edge networks.', icon: Globe },
            { title: 'Resilient', description: 'Unaffected by database outages or query bottlenecks.', icon: Database },
            { title: 'Transparent', description: 'The entire registry is an open-source JSON file, publicly auditable.', icon: Code },
        ],
        content: (
            <>
                <p className="mb-6">
                    The ASAP Protocol completely eliminates the need for complex database setups or heavy infrastructure for basic service discovery. Instead, it leverages a <strong className="font-semibold text-white">Lite Registry</strong>: a statically served, JSON-based index of all available agents within the network.
                </p>
                <h3 className="mb-4 mt-8 text-2xl font-bold text-white">How it Works</h3>
                <p className="mb-6">
                    When you want to register an agent, you submit a pull request containing your agent manifest. Once verified and merged, the deployment pipeline updates a single, statically hosted <code className="rounded bg-zinc-800 px-1 py-0.5 text-sm text-indigo-300">registry.json</code> file.
                </p>
                <ul className="mb-6 ml-6 list-disc space-y-2">
                    <li><strong className="font-semibold text-white">CDN-Optimized:</strong> Delivered instantaneously across global Edge networks.</li>
                    <li><strong className="font-semibold text-white">Resilient:</strong> Unaffected by database outages or query bottlenecks.</li>
                    <li><strong className="font-semibold text-white">Transparent:</strong> The entire registry is an open-source JSON file, publicly auditable at any time.</li>
                </ul>
                <p>
                    Developers simply query this JSON index to retrieve connection strings and protocol definitions, caching the results locally for lightning-fast orchestration.
                </p>
            </>
        ),
    },
    'verified-trust': {
        title: 'Verified Trust',
        description: 'Rigorous vetting for a secure agent ecosystem.',
        icon: ShieldCheck,
        capabilities: [
            { title: 'Untrusted', description: 'Agents running locally or not officially indexed. No guarantees.', icon: Lock },
            { title: 'Self-Signed', description: 'Registered in the Lite Registry. Ed25519 keys prove publisher identity.', icon: ShieldCheck },
            { title: 'Verified', description: 'Manual IssueOps vetting by the core team. Highest trust tier.', icon: ShieldCheck },
        ],
        content: (
            <>
                <p className="mb-6">
                    Security in autonomous networks cannot be an afterthought. The ASAP Protocol enforces a strict, multi-tiered trust hierarchy to protect end-users from malicious actors and buggy experimental agents.
                </p>
                <h3 className="mb-4 mt-8 text-2xl font-bold text-white">The 3-Tier Hierarchy</h3>
                <p className="mb-6">
                    Agents resolving within the protocol are categorized into three distinct security tiers:
                </p>
                <ol className="mb-6 ml-6 list-decimal space-y-2">
                    <li><strong className="font-semibold text-white">Untrusted / Self-hosted:</strong> Agents running locally or not officially indexed. No guarantees.</li>
                    <li><strong className="font-semibold text-white">Self-Signed (Indexed):</strong> Registered in the Lite Registry. Connections are secured via public/private key pairs (Ed25519) established during registration, proving the publisher&apos;s identity.</li>
                    <li><strong className="font-semibold text-white">Verified:</strong> The highest tier. Agents undergo a Manual IssueOps vetting process by the core protocol team, auditing their infrastructure, manifest claims, and data handling practices.</li>
                </ol>
                <p>
                    This combination of cryptographic signing (Ed25519 signatures validating manifest payloads) and human-in-the-loop auditing ensures a safe marketplace for enterprise integration.
                </p>
            </>
        ),
    },
    '1-click-integration': {
        title: '1-Click Integration',
        description: 'Instantly launch and orchestrate agents natively over WebSockets.',
        icon: Zap,
        capabilities: [
            { title: 'Universal Connection', description: 'Secure WebSockets enable bidirectional streaming without HTTP timeouts.', icon: Zap },
            { title: 'Standard Schema', description: 'Inputs defined by manifest schema. Validation before work begins.', icon: Code },
            { title: 'No SDK Lock-in', description: 'Any language with WebSocket support can integrate. SDKs are optional.', icon: Globe },
        ],
        content: (
            <>
                <p className="mb-6">
                    Gone are the days of reading dozens of disparate API documentations. ASAP provides a unified, standard interface for communicating with any agent, regardless of its underlying LLM, architecture, or host platform.
                </p>
                <h3 className="mb-4 mt-8 text-2xl font-bold text-white">The <code>.process</code> Standard</h3>
                <p className="mb-6">
                    Integration is reduced to establishing a connection and issuing a standardized command. All ASAP-compliant agents understand the same core vocabulary:
                </p>
                <ul className="mb-6 ml-6 list-disc space-y-2">
                    <li><strong className="font-semibold text-white">Universal Connection:</strong> Agents communicate over secure WebSockets, enabling bidirectional streaming and long-lived task execution without HTTP timeouts.</li>
                    <li><strong className="font-semibold text-white">Standard Schema:</strong> Define inputs dynamically based on the agent&apos;s published manifest schema. The protocol strictly enforces validation before the agent ever begins work.</li>
                    <li><strong className="font-semibold text-white">No SDK Lock-in:</strong> Any language capable of opening a WebSocket can integrate an ASAP agent. SDKs are optional conveniences, not mandatory dependencies.</li>
                </ul>
                <p>
                    Discover an agent, read its JSON schema, and launch it. It is that simple.
                </p>
            </>
        ),
    },
    'full-observability': {
        title: 'Full Observability',
        description: 'Real-time state streaming and standardized task telemetrics.',
        icon: Activity,
        capabilities: [
            { title: 'Live Event Stream', description: 'Immediate updates as agents change states (started, processing, completed).', icon: Activity },
            { title: 'State Snapshots', description: 'Internal memory snapshots for intermediate UI or real-time debug.', icon: Database },
            { title: 'Structured Logging', description: 'ASAP JSON format with Trace IDs for audit across multi-agent clusters.', icon: Code },
        ],
        content: (
            <>
                <p className="mb-6">
                    When you hand off critical operations to autonomous agents, you cannot accept a &quot;black box&quot; architecture. You need to know exactly what the agent is doing, what decisions it is making, and when it fails.
                </p>
                <h3 className="mb-4 mt-8 text-2xl font-bold text-white">Protocol Guarantees</h3>
                <p className="mb-6">
                    The ASAP Protocol mandates that all agents emit a standardized stream of operational telemetry back to the consumer:
                </p>
                <ul className="ml-6 list-disc space-y-2">
                    <li><strong className="font-semibold text-white">Live Event Stream:</strong> Receive immediate updates as the agent changes states (e.g., <code className="rounded bg-zinc-800 px-1 py-0.5 text-sm text-indigo-300">started</code>, <code className="rounded bg-zinc-800 px-1 py-0.5 text-sm text-indigo-300">processing</code>, <code className="rounded bg-zinc-800 px-1 py-0.5 text-sm text-indigo-300">waiting_for_input</code>, <code className="rounded bg-zinc-800 px-1 py-0.5 text-sm text-indigo-300">completed</code>).</li>
                    <li><strong className="font-semibold text-white">State Snapshots:</strong> For complex, multi-step chains of thought, agents emit their internal memory snapshots, allowing consumers to render intermediate UI elements or debug logic in real-time.</li>
                    <li><strong className="font-semibold text-white">Structured Logging:</strong> All errors and warnings follow the rigorous ASAP JSON structured logging format, complete with Trace IDs, ensuring you can audit the exact point of failure across a multi-agent orchestrated cluster.</li>
                </ul>
            </>
        ),
    },
};

export async function generateMetadata({
    params,
}: {
    params: Promise<{ slug: string }>;
}): Promise<Metadata> {
    const { slug } = await params;
    const feature = FEATURE_CONTENT[slug];
    if (!feature) return { title: 'Feature Not Found | ASAP Protocol' };
    return {
        title: `${feature.title} | ASAP Protocol`,
        description: feature.description,
    };
}

export default async function FeatureDetail({ params }: { params: Promise<{ slug: string }> }) {
    const p = await params;
    const feature = FEATURE_CONTENT[p.slug];

    if (!feature) {
        notFound();
    }

    const Icon = feature.icon;

    return (
        <main className="min-h-screen bg-zinc-950 font-sans text-white selection:bg-indigo-500/30">
            {/* Decorative gradient blur */}
            <div className="absolute top-0 -z-10 h-full w-full bg-zinc-950">
                <div className="absolute left-1/2 right-0 top-0 -z-10 -ml-24 h-[600px] w-[600px] rounded-full bg-indigo-900/20 blur-[120px]" />
            </div>

            <div className="container mx-auto px-4 py-16 sm:px-6 lg:px-8">
                <div className="mb-8">
                    <Link
                        href="/#features"
                        className="group flex items-center text-sm font-medium text-zinc-400 transition-colors hover:text-white"
                    >
                        <ArrowLeft className="mr-2 h-4 w-4 transition-transform group-hover:-translate-x-1" />
                        Back to Home
                    </Link>
                </div>

                <article className="mx-auto max-w-3xl">
                    <header className="mb-12">
                        <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl border border-zinc-800 bg-zinc-900/50">
                            <Icon className="h-8 w-8 text-indigo-400" />
                        </div>
                        <h1 className="mb-4 text-4xl font-extrabold tracking-tight text-white sm:text-5xl">
                            {feature.title}
                        </h1>
                        <p className="text-xl text-zinc-400">{feature.description}</p>
                    </header>

                    <div className="space-y-6 text-lg leading-relaxed">
                        {feature.content}
                    </div>

                    <div className="mt-12">
                        <h2 className="mb-6 text-2xl font-bold tracking-tight text-white">
                            Key Capabilities
                        </h2>
                        <BentoGrid>
                            {feature.capabilities.map((cap) => (
                                <BentoCard
                                    key={cap.title}
                                    icon={cap.icon}
                                    title={cap.title}
                                    description={cap.description}
                                />
                            ))}
                        </BentoGrid>
                    </div>

                    <div className="mt-16 border-t border-zinc-800 pt-8 text-center">
                        <h2 className="mb-6 text-2xl font-bold tracking-tight text-white">
                            Ready to explore the marketplace?
                        </h2>
                        <Link
                            href="/browse"
                            className="inline-flex h-12 items-center justify-center rounded-md bg-white px-8 text-sm font-medium text-zinc-950 transition-colors hover:bg-zinc-200 focus:outline-none focus:ring-2 focus:ring-zinc-400 focus:ring-offset-2 focus:ring-offset-zinc-950"
                        >
                            Browse Agents
                        </Link>
                    </div>
                </article>
            </div>
        </main>
    );
}
