'use client';

import { Manifest } from '@/types/protocol';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { TerminalSquare, PlusCircle, Activity, Key, BarChart3, Globe, ShieldAlert, Loader2, GitPullRequest, ExternalLink, ShieldCheck, RefreshCw } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
import useSWR from 'swr';
import { fetchUserRegistrationIssues } from './actions';

export type PendingRegistration = {
    id: number;
    number: number;
    title: string;
    url: string;
    state: string;
    status: string;
};

interface DashboardClientProps {
    initialAgents: Manifest[];
    username: string;
}

// Client-side component to fetch and display agent status via server proxy (avoids exposing user IP to agents)
function AgentStatusBadge({ endpoint }: { endpoint: string }) {
    const [status, setStatus] = useState<'pending' | 'online' | 'offline'>('pending');

    useEffect(() => {
        let isMounted = true;
        const checkStatus = async () => {
            if (!endpoint) {
                if (isMounted) setStatus('offline');
                return;
            }
            try {
                const proxyUrl = `/api/health-check?url=${encodeURIComponent(endpoint)}`;
                const res = await fetch(proxyUrl);
                const data = (await res.json()) as { ok?: boolean };
                if (isMounted) {
                    setStatus(data.ok ? 'online' : 'offline');
                }
            } catch {
                if (isMounted) {
                    setStatus('offline');
                }
            }
        };

        checkStatus();
        return () => { isMounted = false; };
    }, [endpoint]);

    if (status === 'pending') {
        return (
            <Badge variant="outline" className="text-[10px] bg-muted text-muted-foreground border-muted-foreground/30 px-2 py-0 flex items-center gap-1">
                <Loader2 className="w-3 h-3 animate-spin" /> Checking
            </Badge>
        );
    }

    if (status === 'online') {
        return (
            <Badge variant="outline" className="text-[10px] bg-emerald-500/10 text-emerald-500 border-emerald-500/20 px-2 py-0">
                Online
            </Badge>
        );
    }

    return (
        <Badge variant="outline" className="text-[10px] bg-red-500/10 text-red-500 border-red-500/20 px-2 py-0">
            Offline
        </Badge>
    );
}

export function DashboardClient({ initialAgents, username }: DashboardClientProps) {
    const router = useRouter();
    const [isRefreshing, setIsRefreshing] = useState(false);
    const { data: pendingIssuesData, mutate } = useSWR('userRegistrationIssues', async () => {
        const res = await fetchUserRegistrationIssues();
        if (res.success && res.data) return res.data as PendingRegistration[];
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

                {/* Pending registration issues (IssueOps): open issues with label "registration" by this user */}
                {pendingRegistrations.length > 0 && (
                    <div className="space-y-3 mb-6">
                        <h3 className="text-sm font-medium text-muted-foreground">Pending Registrations</h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {pendingRegistrations.map((issue) => (
                                <Card key={issue.id} className="bg-muted/30 border-dashed">
                                    <CardContent className="p-4 space-y-3">
                                        <div className="flex items-center justify-between gap-3">
                                            <div className="flex items-center gap-3 min-w-0">
                                                <div className="p-2 bg-indigo-500/10 text-indigo-500 rounded-full shrink-0">
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
                        <CardContent className="flex flex-col items-center justify-center py-16 text-center space-y-4">
                            <div className="p-4 bg-muted rounded-full">
                                <TerminalSquare className="w-8 h-8 text-muted-foreground" />
                            </div>
                            <div className="max-w-md">
                                <h3 className="font-semibold text-lg">No agents found</h3>
                                <p className="text-sm text-muted-foreground mt-1 mb-4">
                                    You haven&apos;t registered any agents under the username <span className="font-mono">{username}</span> yet.
                                </p>
                                <Button asChild variant="outline">
                                    <Link href="/dashboard/register">Register your first agent</Link>
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                ) : (
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
                                            <AgentStatusBadge endpoint={agent.endpoints.asap ?? ''} />
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
