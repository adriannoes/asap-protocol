'use client';

import type { RegistryAgent } from '@/types/registry';
import { isAllowedExternalUrl } from '@/lib/url-validator';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { ArrowLeft, ExternalLink, ShieldAlert, ShieldCheck, TerminalSquare, Loader2 } from 'lucide-react';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { Code2 } from 'lucide-react';

interface AgentDetailClientProps {
    agent: RegistryAgent;
}

function AgentReachabilityBadge({ endpoint, skipReachabilityCheck }: { endpoint: string; skipReachabilityCheck?: boolean }) {
    const [status, setStatus] = useState<'pending' | 'online' | 'offline'>('pending');

    useEffect(() => {
        if (skipReachabilityCheck) return;
        let isMounted = true;
        const check = async () => {
            if (!endpoint) {
                if (isMounted) setStatus('offline');
                return;
            }
            try {
                const res = await fetch(`/api/proxy/check?url=${encodeURIComponent(endpoint)}`);
                const data = (await res.json()) as { ok?: boolean };
                if (isMounted) setStatus(data.ok ? 'online' : 'offline');
            } catch {
                if (isMounted) setStatus('offline');
            }
        };
        check();
        return () => { isMounted = false };
    }, [endpoint, skipReachabilityCheck]);

    if (skipReachabilityCheck) {
        return (
            <Badge variant="outline" className="text-xs bg-muted text-muted-foreground border-muted-foreground/30">
                Demo
            </Badge>
        );
    }
    if (status === 'pending') {
        return (
            <Badge variant="outline" className="text-xs bg-muted text-muted-foreground border-muted-foreground/30 gap-1">
                <Loader2 className="w-3 h-3 animate-spin" /> Checking
            </Badge>
        );
    }
    if (status === 'online') {
        return (
            <Badge variant="outline" className="text-xs bg-emerald-500/10 text-emerald-500 border-emerald-500/20">
                Online
            </Badge>
        );
    }
    return (
        <Badge variant="outline" className="text-xs bg-red-500/10 text-red-500 border-red-500/20">
            Offline
        </Badge>
    );
}

function safeAuthHref(url: unknown): string {
    if (typeof url !== 'string') return '#';
    return isAllowedExternalUrl(url).valid ? url : '#';
}

export function AgentDetailClient({ agent }: AgentDetailClientProps) {
    const agentEndpoint = agent.endpoints?.asap ?? (agent.endpoints as { http?: string })?.http;

    const renderBooleanBadge = (value: boolean | undefined | null, label: string) => {
        if (value === undefined || value === null) return null;
        return (
            <Badge variant={value ? "default" : "secondary"}>
                {label}: {value ? 'Yes' : 'No'}
            </Badge>
        );
    };

    return (
        <div className="space-y-8">
            {/* Back Navigation */}
            <div>
                <Button variant="ghost" asChild className="-ml-4 mb-2">
                    <Link href="/browse" className="text-muted-foreground flex items-center">
                        <ArrowLeft className="mr-2 h-4 w-4" />
                        Back to Registry
                    </Link>
                </Button>

                <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                    <div>
                        <h1 className="text-3xl font-bold tracking-tight">{agent.name}</h1>
                        <p className="text-muted-foreground mt-2 max-w-2xl text-lg">
                            {agent.description}
                        </p>
                        <div className="flex flex-wrap items-center mt-4 gap-2">
                            <Badge variant="outline" className="text-xs font-mono py-1">
                                {agent.id}
                            </Badge>
                            {agent.version && (
                                <Badge variant="secondary" className="text-xs">
                                    v{agent.version}
                                </Badge>
                            )}
                            {agent.built_with && (
                                <Badge variant="outline" className="text-xs">
                                    {agent.built_with}
                                </Badge>
                            )}
                            {agent.sla ? (
                                <Badge variant="default" className="bg-emerald-600 hover:bg-emerald-700 flex items-center gap-1">
                                    <ShieldCheck className="w-3 h-3" />
                                    Verified SLA
                                </Badge>
                            ) : null}
                            {agent.auth?.schemes && agent.auth.schemes.length > 0 ? (
                                <Badge variant="outline" className="flex items-center gap-1">
                                    <ShieldAlert className="w-3 h-3" />
                                    Auth Required
                                </Badge>
                            ) : null}
                            {agentEndpoint && <AgentReachabilityBadge endpoint={agentEndpoint} skipReachabilityCheck={agent.online_check === false} />}
                        </div>
                    </div>

                    <div className="flex flex-col gap-3 min-w-48 shrink-0">
                        <Button className="w-full font-semibold shadow-md gap-2" size="lg">
                            <TerminalSquare className="w-4 h-4" /> Connect Agent
                        </Button>
                        <div className="p-3 bg-muted/50 border rounded-md text-xs font-mono break-all selection:bg-indigo-500/30">
                            {agent.endpoints?.asap ?? (agent.endpoints as { http?: string })?.http}
                        </div>
                        {(agent.repository_url || agent.documentation_url) && (
                            <div className="flex flex-wrap gap-2">
                                {agent.repository_url && (
                                    <Button variant="outline" size="sm" className="text-xs" asChild>
                                        <a href={agent.repository_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1">
                                            <ExternalLink className="w-3 h-3" /> Repository
                                        </a>
                                    </Button>
                                )}
                                {agent.documentation_url && (
                                    <Button variant="outline" size="sm" className="text-xs" asChild>
                                        <a href={agent.documentation_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1">
                                            <ExternalLink className="w-3 h-3" /> Documentation
                                        </a>
                                    </Button>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="md:col-span-2 space-y-6">
                    {/* Developer Quick Start */}
                    <Card className="border-indigo-500/20 shadow-sm shadow-indigo-500/5">
                        <CardHeader className="pb-3">
                            <CardTitle className="text-lg flex items-center gap-2">
                                <Code2 className="w-5 h-5 text-indigo-400" />
                                Developer Quick Start
                            </CardTitle>
                            <CardDescription>
                                Connect to this agent using the official ASAP Client.
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="group relative rounded-md bg-zinc-950 p-4 font-mono text-sm text-zinc-300 border border-zinc-800 overflow-x-auto">
                                <pre className="leading-relaxed">
                                    <span className="text-zinc-500"># 1. Install the client</span>{'\n'}
                                    <span className="text-indigo-400">npm</span> install @asap/client{'\n\n'}
                                    <span className="text-zinc-500"># 2. Connect and route requests</span>{'\n'}
                                    <span className="text-purple-400">import</span> {'{'} AsapClient {'}'} <span className="text-purple-400">from</span> <span className="text-emerald-300">&apos;@asap/client&apos;</span>;{'\n\n'}
                                    <span className="text-purple-400">const</span> client = <span className="text-purple-400">new</span> AsapClient();{'\n'}
                                    <span className="text-purple-400">await</span> client.connect(<span className="text-emerald-300">&apos;{agent.id}&apos;</span>);{'\n\n'}
                                    <span className="text-purple-400">const</span> response = <span className="text-purple-400">await</span> client.sendTask({'{'}{'\n'}
                                    {'  '}skill: <span className="text-emerald-300">&apos;{Array.isArray(agent.capabilities?.skills) && agent.capabilities.skills.length > 0 ? (agent.capabilities.skills[0] as { id: string }).id : 'example-skill'}&apos;</span>,{'\n'}
                                    {'  '}input: {'{ /* payload */ }'}{'\n'}
                                    {'}'});
                                </pre>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Skills and Capabilities */}
                    <Card>
                        <CardHeader>
                            <CardTitle>Capabilities & Skills</CardTitle>
                            <CardDescription>
                                Discover what this agent can do via ASAP Protocol.
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            <div className="flex flex-wrap gap-2 mb-4 cursor-default">
                                {renderBooleanBadge(agent.capabilities?.state_persistence, 'State Persistence')}
                                {renderBooleanBadge(agent.capabilities?.streaming, 'Streaming')}
                                {agent.capabilities?.asap_version && (
                                    <Badge variant="outline">ASAP Protocol {agent.capabilities.asap_version}</Badge>
                                )}
                            </div>

                            <Separator />

                            <div className="space-y-4 pt-2">
                                <h3 className="font-semibold text-sm">Registered Skills</h3>
                                {Array.isArray(agent.capabilities?.skills) && agent.capabilities.skills.length > 0 ? (
                                    <div className="space-y-4">
                                        {agent.capabilities.skills.map((skill: { id: string, description: string }) => (
                                            <div key={skill.id} className="p-4 border rounded-lg bg-card/50">
                                                <div className="flex justify-between items-start mb-2">
                                                    <h4 className="font-semibold text-sm font-mono text-indigo-400">{skill.id}</h4>
                                                </div>
                                                <p className="text-sm text-muted-foreground">{skill.description}</p>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <p className="text-sm text-muted-foreground italic">No specific skills listed.</p>
                                )}
                            </div>
                        </CardContent>
                    </Card>
                </div>

                <div className="space-y-6">
                    {/* SLA Section */}
                    <Card>
                        <CardHeader>
                            <CardTitle>Service Level</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            {agent.sla ? (
                                <div className="space-y-3 text-sm">
                                    <div className="flex justify-between items-center py-1 border-b border-border/50">
                                        <span className="text-muted-foreground">Availability</span>
                                        <span className="font-medium">{agent.sla.availability || 'N/A'}</span>
                                    </div>
                                    <div className="flex justify-between items-center py-1 border-b border-border/50">
                                        <span className="text-muted-foreground">Latency (p95)</span>
                                        <span className="font-medium">{agent.sla.max_latency_p95_ms ? `${agent.sla.max_latency_p95_ms}ms` : 'N/A'}</span>
                                    </div>
                                    <div className="flex justify-between items-center py-1 border-b border-border/50">
                                        <span className="text-muted-foreground">Error Rate</span>
                                        <span className="font-medium">{agent.sla.max_error_rate || 'N/A'}</span>
                                    </div>
                                    <div className="flex justify-between items-center py-1">
                                        <span className="text-muted-foreground">Support</span>
                                        <span className="font-medium">{agent.sla.support_hours || 'N/A'}</span>
                                    </div>
                                </div>
                            ) : (
                                <div className="text-center py-4 text-sm text-muted-foreground">
                                    <p>This agent has no published SLA.</p>
                                    <p className="mt-1">Performance is not guaranteed.</p>
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    {/* Auth Requirements */}
                    <Card>
                        <CardHeader>
                            <CardTitle>Authentication</CardTitle>
                        </CardHeader>
                        <CardContent>
                            {agent.auth?.schemes && agent.auth.schemes.length > 0 ? (
                                <div className="space-y-4">
                                    <div className="flex flex-wrap gap-2">
                                        {agent.auth.schemes.map(s => (
                                            <Badge key={s} variant="secondary">{s}</Badge>
                                        ))}
                                    </div>
                                    {agent.auth.oauth2 && (
                                        <div className="text-xs text-muted-foreground mt-4 space-y-1">
                                            <p>OAuth2 Setup available.</p>
                                            <p className="flex items-center gap-1 group">
                                                <ExternalLink className="w-3 h-3 group-hover:text-indigo-400" />
                                                <a
                                                    href={safeAuthHref(agent.auth.oauth2?.authorization_url)}
                                                    target="_blank"
                                                    rel="noreferrer"
                                                    className="group-hover:text-indigo-400 underline decoration-border underline-offset-2"
                                                >
                                                    Auth URL
                                                </a>
                                            </p>
                                        </div>
                                    )}
                                </div>
                            ) : (
                                <p className="text-sm text-muted-foreground">No authentication required.</p>
                            )}
                        </CardContent>
                    </Card>

                </div>
            </div>
        </div>
    );
}
