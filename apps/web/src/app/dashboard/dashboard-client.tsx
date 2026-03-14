'use client';

import type { RegistryAgent } from '@/types/registry';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { PackageSearch, PlusCircle, Activity, Key, BarChart3, Globe, ShieldAlert, GitPullRequest, ExternalLink, ShieldCheck, RefreshCw, Workflow, Bot, Shield } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCallback, useState } from 'react';
import useSWR from 'swr';
import {
    fetchUserRegistrationIssues,
    revalidateUserRegistrationIssues,
} from './actions';
import { AgentStatusBadge } from '@/components/agent/agent-status-badge';
import { EmptyState } from '@/components/ui/empty-state';
import { AGENT_BUILDER_URL_WITH_FROM } from '@/lib/agent-builder-url';
import { BentoGrid, BentoCard } from '@/components/ui/bento-grid';

export type PendingRegistration = {
    id: number;
    number: number;
    title: string;
    url: string;
    state: string;
    status: string;
};

interface DashboardClientProps {
    initialAgents: RegistryAgent[];
    username: string;
}

export function DashboardClient({ initialAgents, username: _username }: DashboardClientProps) {
    const router = useRouter();
    const [isRefreshing, setIsRefreshing] = useState(false);
    const { data: pendingIssuesData, mutate } = useSWR('userRegistrationIssues', async () => {
        const res = await fetchUserRegistrationIssues();
        if (res.success && 'data' in res) return res.data as PendingRegistration[];
        return [];
    }, {
        refreshInterval: 60_000,
        onErrorRetry: (_error, _key, _config, revalidate, { retryCount }) => {
            if (retryCount >= 3) return;
            setTimeout(() => revalidate({ retryCount }), 5000 * (retryCount + 1));
        },
    });

    const pendingRegistrations = pendingIssuesData ?? [];

    const handleRefresh = useCallback(async () => {
        setIsRefreshing(true);
        await revalidateUserRegistrationIssues();
        await mutate();
        router.refresh();
        setIsRefreshing(false);
    }, [mutate, router]);

    return (
        <Tabs defaultValue="agents" className="space-y-6">
            <TabsList className="grid w-full grid-cols-3 max-w-md">
                <TabsTrigger value="agents">
                    My Agents{pendingRegistrations.length > 0 ? ` (${pendingRegistrations.length} pending)` : ''}
                </TabsTrigger>
                <TabsTrigger value="metrics">Usage Metrics</TabsTrigger>
                <TabsTrigger value="keys">API Keys</TabsTrigger>
            </TabsList>

            <TabsContent value="agents" className="space-y-6">
                <Card className="bg-gradient-to-r from-indigo-500/10 to-purple-500/10 border-indigo-500/20">
                    <CardContent className="p-4 flex items-center gap-4">
                        <div className="p-3 bg-indigo-500/10 rounded-lg border border-indigo-500/20 shrink-0">
                            <Workflow className="w-6 h-6 text-indigo-400" />
                        </div>
                        <div className="flex-1 min-w-0">
                            <h3 className="font-semibold text-sm">Agent Builder</h3>
                            <p className="text-xs text-muted-foreground mt-0.5">
                                Design, connect, and run AI agents visually with our drag-and-drop builder.
                            </p>
                        </div>
                        <Button asChild variant="outline" size="sm" className="shrink-0 border-indigo-500/30 text-indigo-400 hover:bg-indigo-500/10">
                            <a
                                href={AGENT_BUILDER_URL_WITH_FROM}
                                className="flex items-center gap-1.5"
                            >
                                Open Agent Builder
                                <ExternalLink className="w-3 h-3" />
                            </a>
                        </Button>
                    </CardContent>
                </Card>
                <div className="flex justify-between items-center flex-wrap gap-4">
                    <div>
                        <h2 className="text-xl font-semibold tracking-tight">Registered Agents</h2>
                        <p className="text-sm text-muted-foreground">Manage your published agents on the ASAP Protocol.</p>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button variant="outline" size="sm" onClick={handleRefresh} disabled={isRefreshing} className="gap-2">
                            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} /> Refresh
                        </Button>
                        <Button asChild>
                            <Link href="/dashboard/register" className="flex items-center gap-2">
                                <PlusCircle className="w-4 h-4" /> Register New Agent
                            </Link>
                        </Button>
                    </div>
                </div>

                {pendingRegistrations.length > 0 && (
                    <div className="space-y-3 mb-6">
                        <h3 className="text-sm font-medium text-muted-foreground">Pending Registrations</h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {pendingRegistrations.map((issue) => (
                                <Card key={issue.id} className="bg-muted/30 border-dashed">
                                    <CardContent className="p-4 space-y-3">
                                        <div className="flex items-center justify-between gap-3">
                                            <div className="flex items-center gap-3 min-w-0">
                                                <div className="p-2 bg-indigo-500/10 text-indigo-500 rounded-[--radius] shrink-0">
                                                    <GitPullRequest className="w-4 h-4" />
                                                </div>
                                                <div className="min-w-0">
                                                    <p className="text-sm font-medium line-clamp-1" title={issue.title}>{issue.title}</p>
                                                    <p className="text-xs text-muted-foreground">Status: <span className="text-yellow-500">{issue.status}</span></p>
                                                </div>
                                            </div>
                                            <Button asChild variant="outline" size="sm" className="shrink-0 text-xs">
                                                <a href={issue.url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1">
                                                    <ExternalLink className="w-3 h-3" /> View issue
                                                </a>
                                            </Button>
                                        </div>
                                        <p className="text-xs text-muted-foreground">
                                            If validation failed, the comment on the issue shows the reason. You can fix and re-edit the issue.
                                        </p>
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    </div>
                )}

                {initialAgents.length === 0 && pendingRegistrations.length > 0 ? (
                    <Card className="border-dashed bg-muted/30">
                        <CardContent className="flex flex-col items-center justify-center py-12 text-center space-y-4">
                            <div className="max-w-md">
                                <p className="text-sm text-muted-foreground">
                                    You have pending registration(s). Open the issue link above to check if it was accepted or if there&apos;s feedback to fix.
                                </p>
                            </div>
                        </CardContent>
                    </Card>
                ) : initialAgents.length === 0 ? (
                    <Card className="border-dashed bg-muted/30">
                        <CardContent className="p-0">
                            <EmptyState
                                icon={PackageSearch}
                                title="No agents found"
                                description="You haven't registered any agents yet."
                                actionLabel="Register your first agent"
                                actionHref="/dashboard/register"
                            />
                        </CardContent>
                    </Card>
                ) : (
                    <>
                        <BentoGrid className="mb-8">
                            <BentoCard
                                icon={Bot}
                                title="Total Agents"
                                value={initialAgents.length}
                                description="Registered agents in your account"
                                className="md:col-span-2"
                            />
                            <BentoCard
                                icon={Activity}
                                title="Active Tasks"
                                value={0}
                                description="Currently running task sessions"
                            />
                            <BentoCard
                                icon={Shield}
                                title="Verified"
                                value={initialAgents.filter((a) => a.verification?.status === 'verified').length}
                                description="Agents with verified trust badges"
                            />
                        </BentoGrid>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {initialAgents.map(agent => (
                            <Card key={agent.id ?? ''}>
                                <CardHeader className="pb-4">
                                    <div className="flex justify-between items-start gap-2">
                                        <CardTitle className="text-lg line-clamp-1 min-w-0" title={agent.name ?? ''}>{agent.name}</CardTitle>
                                        <div className="flex flex-wrap items-center gap-1.5 shrink-0 justify-end">
                                            <Badge variant="outline" className="text-[10px] bg-zinc-500/10 text-zinc-600 dark:text-zinc-400 border-zinc-500/20 px-2 py-0 font-normal">
                                                Listed
                                            </Badge>
                                            {String(agent.verification?.status) === 'verified' && (
                                                <Badge variant="outline" className="text-[10px] bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 px-2 py-0 flex items-center gap-0.5">
                                                    <ShieldCheck className="w-3 h-3" /> Verified
                                                </Badge>
                                            )}
                                            <AgentStatusBadge endpoint={agent.endpoints?.asap ?? ''} skipReachabilityCheck={agent.online_check === false} size="sm" />
                                        </div>
                                    </div>
                                    <CardDescription className="text-xs font-mono truncate" title={agent.id ?? ''}>{agent.id}</CardDescription>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    <div className="text-sm text-muted-foreground line-clamp-2 min-h-10" title={agent.description ?? ''}>
                                        {agent.description}
                                    </div>
                                    <div className="flex items-center gap-1 text-xs bg-muted/50 p-2 rounded-md font-mono overflow-hidden" title={agent.endpoints.asap ?? ''}>
                                        <Globe className="w-3 h-3 shrink-0 text-muted-foreground" />
                                        <span className="truncate">{agent.endpoints.asap}</span>
                                    </div>
                                </CardContent>
                                <CardFooter className="pt-4 border-t flex flex-wrap gap-2">
                                    <Button variant="outline" size="sm" className="text-xs" asChild>
                                        <Link href={`/agents/${encodeURIComponent(agent.id ?? '')}`}>View Profile</Link>
                                    </Button>
                                    <Button variant="secondary" size="sm" className="text-xs" asChild>
                                        <Link href={`/dashboard/agents/${encodeURIComponent(agent.id ?? '')}/edit`}>Edit</Link>
                                    </Button>
                                    {String(agent.verification?.status) !== 'verified' && (
                                        <Button variant="outline" size="sm" className="text-xs border-amber-500/30 text-amber-600 dark:text-amber-400" asChild>
                                            <Link href={`/dashboard/verify?agent_id=${encodeURIComponent(agent.id ?? '')}`} className="flex items-center gap-1">
                                                <ShieldCheck className="w-3 h-3" /> Apply for Verified
                                            </Link>
                                        </Button>
                                    )}
                                </CardFooter>
                            </Card>
                        ))}
                        </div>
                    </>
                )}
            </TabsContent>

            <TabsContent value="metrics" className="space-y-4">
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <BarChart3 className="w-5 h-5" /> Usage Metrics
                        </CardTitle>
                        <CardDescription>
                            Aggregated metrics for all your agents.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="flex flex-col items-center justify-center py-12 text-center">
                            <Activity className="w-12 h-12 text-muted-foreground mb-4 opacity-20" />
                            <h3 className="text-lg font-medium">Metrics coming soon</h3>
                            <p className="text-sm text-muted-foreground mt-2 max-w-sm">
                                Network-wide request volumes, failure rates, and latencies will be aggregated here in a future update.
                            </p>
                        </div>
                    </CardContent>
                </Card>
            </TabsContent>

            <TabsContent value="keys" className="space-y-4">
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Key className="w-5 h-5" /> API Keys
                        </CardTitle>
                        <CardDescription>
                            Manage API keys for programmatic access to your dashboard and agent publishing.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="flex flex-col items-center justify-center py-12 text-center">
                            <ShieldAlert className="w-12 h-12 text-muted-foreground mb-4 opacity-20" />
                            <h3 className="text-lg font-medium">No keys generated</h3>
                            <p className="text-sm text-muted-foreground mt-2 max-w-sm">
                                You currently don&apos;t have any active API keys. Use OAuth via GitHub for CLI interactions right now.
                            </p>
                            <Button className="mt-6" variant="outline" disabled>Generate New Key</Button>
                        </div>
                    </CardContent>
                </Card>
            </TabsContent>
        </Tabs>
    );
}
