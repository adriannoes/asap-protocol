'use client';

import type { RegistryAgent } from '@/types/registry';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  CardFooter,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  PackageSearch,
  PlusCircle,
  Activity,
  Key,
  BarChart3,
  Globe,
  ShieldAlert,
  GitPullRequest,
  ExternalLink,
  ShieldCheck,
  RefreshCw,
  Workflow,
  Bot,
  Shield,
} from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCallback, useState } from 'react';
import useSWR from 'swr';
import { fetchUserRegistrationIssues, revalidateUserRegistrationIssues } from './actions';
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
  const { data: pendingIssuesData, mutate } = useSWR(
    'userRegistrationIssues',
    async () => {
      const res = await fetchUserRegistrationIssues();
      if (res.success && 'data' in res) return res.data as PendingRegistration[];
      return [];
    },
    {
      refreshInterval: 60_000,
      onErrorRetry: (_error, _key, _config, revalidate, { retryCount }) => {
        if (retryCount >= 3) return;
        setTimeout(() => revalidate({ retryCount }), 5000 * (retryCount + 1));
      },
    }
  );

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
      <TabsList className="grid w-full max-w-md grid-cols-3">
        <TabsTrigger value="agents">
          My Agents
          {pendingRegistrations.length > 0 ? ` (${pendingRegistrations.length} pending)` : ''}
        </TabsTrigger>
        <TabsTrigger value="metrics">Usage Metrics</TabsTrigger>
        <TabsTrigger value="keys">API Keys</TabsTrigger>
      </TabsList>

      <TabsContent value="agents" className="space-y-6">
        <Card className="border-indigo-500/20 bg-gradient-to-r from-indigo-500/10 to-purple-500/10">
          <CardContent className="flex items-center gap-4 p-4">
            <div className="shrink-0 rounded-lg border border-indigo-500/20 bg-indigo-500/10 p-3">
              <Workflow className="h-6 w-6 text-indigo-400" />
            </div>
            <div className="min-w-0 flex-1">
              <h3 className="text-sm font-semibold">Agent Builder</h3>
              <p className="text-muted-foreground mt-0.5 text-xs">
                Design, connect, and run AI agents visually with our drag-and-drop builder.
              </p>
            </div>
            <Button
              asChild
              variant="outline"
              size="sm"
              className="shrink-0 border-indigo-500/30 text-indigo-400 hover:bg-indigo-500/10"
            >
              <a href={AGENT_BUILDER_URL_WITH_FROM} className="flex items-center gap-1.5">
                Open Agent Builder
                <ExternalLink className="h-3 w-3" />
              </a>
            </Button>
          </CardContent>
        </Card>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold tracking-tight">Registered Agents</h2>
            <p className="text-muted-foreground text-sm">
              Manage your published agents on the ASAP Protocol.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="gap-2"
            >
              <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} /> Refresh
            </Button>
            <Button asChild>
              <Link href="/dashboard/register" className="flex items-center gap-2">
                <PlusCircle className="h-4 w-4" /> Register New Agent
              </Link>
            </Button>
          </div>
        </div>

        {pendingRegistrations.length > 0 && (
          <div className="mb-6 space-y-3">
            <h3 className="text-muted-foreground text-sm font-medium">Pending Registrations</h3>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {pendingRegistrations.map((issue) => (
                <Card key={issue.id} className="bg-muted/30 border-dashed">
                  <CardContent className="space-y-3 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex min-w-0 items-center gap-3">
                        <div className="shrink-0 rounded-[--radius] bg-indigo-500/10 p-2 text-indigo-500">
                          <GitPullRequest className="h-4 w-4" />
                        </div>
                        <div className="min-w-0">
                          <p className="line-clamp-1 text-sm font-medium" title={issue.title}>
                            {issue.title}
                          </p>
                          <p className="text-muted-foreground text-xs">
                            Status: <span className="text-yellow-500">{issue.status}</span>
                          </p>
                        </div>
                      </div>
                      <Button asChild variant="outline" size="sm" className="shrink-0 text-xs">
                        <a
                          href={issue.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1"
                        >
                          <ExternalLink className="h-3 w-3" /> View issue
                        </a>
                      </Button>
                    </div>
                    <p className="text-muted-foreground text-xs">
                      If validation failed, the comment on the issue shows the reason. You can fix
                      and re-edit the issue.
                    </p>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}

        {initialAgents.length === 0 && pendingRegistrations.length > 0 ? (
          <Card className="bg-muted/30 border-dashed">
            <CardContent className="flex flex-col items-center justify-center space-y-4 py-12 text-center">
              <div className="max-w-md">
                <p className="text-muted-foreground text-sm">
                  You have pending registration(s). Open the issue link above to check if it was
                  accepted or if there&apos;s feedback to fix.
                </p>
              </div>
            </CardContent>
          </Card>
        ) : initialAgents.length === 0 ? (
          <Card className="bg-muted/30 border-dashed">
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
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
              {initialAgents.map((agent) => (
                <Card key={agent.id ?? ''}>
                  <CardHeader className="pb-4">
                    <div className="flex items-start justify-between gap-2">
                      <CardTitle className="line-clamp-1 min-w-0 text-lg" title={agent.name ?? ''}>
                        {agent.name}
                      </CardTitle>
                      <div className="flex shrink-0 flex-wrap items-center justify-end gap-1.5">
                        <Badge
                          variant="outline"
                          className="border-zinc-500/20 bg-zinc-500/10 px-2 py-0 text-[10px] font-normal text-zinc-600 dark:text-zinc-400"
                        >
                          Listed
                        </Badge>
                        {String(agent.verification?.status) === 'verified' && (
                          <Badge
                            variant="outline"
                            className="flex items-center gap-0.5 border-emerald-500/20 bg-emerald-500/10 px-2 py-0 text-[10px] text-emerald-600 dark:text-emerald-400"
                          >
                            <ShieldCheck className="h-3 w-3" /> Verified
                          </Badge>
                        )}
                        <AgentStatusBadge
                          endpoint={agent.endpoints?.asap ?? ''}
                          skipReachabilityCheck={agent.online_check === false}
                          size="sm"
                        />
                      </div>
                    </div>
                    <CardDescription className="truncate font-mono text-xs" title={agent.id ?? ''}>
                      {agent.id}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div
                      className="text-muted-foreground line-clamp-2 min-h-10 text-sm"
                      title={agent.description ?? ''}
                    >
                      {agent.description}
                    </div>
                    <div
                      className="bg-muted/50 flex items-center gap-1 overflow-hidden rounded-md p-2 font-mono text-xs"
                      title={agent.endpoints.asap ?? ''}
                    >
                      <Globe className="text-muted-foreground h-3 w-3 shrink-0" />
                      <span className="truncate">{agent.endpoints.asap}</span>
                    </div>
                  </CardContent>
                  <CardFooter className="flex flex-wrap gap-2 border-t pt-4">
                    <Button variant="outline" size="sm" className="text-xs" asChild>
                      <Link href={`/agents/${encodeURIComponent(agent.id ?? '')}`}>
                        View Profile
                      </Link>
                    </Button>
                    <Button variant="secondary" size="sm" className="text-xs" asChild>
                      <Link href={`/dashboard/agents/${encodeURIComponent(agent.id ?? '')}/edit`}>
                        Edit
                      </Link>
                    </Button>
                    {String(agent.verification?.status) !== 'verified' && (
                      <Button
                        variant="outline"
                        size="sm"
                        className="border-amber-500/30 text-xs text-amber-600 dark:text-amber-400"
                        asChild
                      >
                        <Link
                          href={`/dashboard/verify?agent_id=${encodeURIComponent(agent.id ?? '')}`}
                          className="flex items-center gap-1"
                        >
                          <ShieldCheck className="h-3 w-3" /> Apply for Verified
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
              <BarChart3 className="h-5 w-5" /> Usage Metrics
            </CardTitle>
            <CardDescription>Aggregated metrics for all your agents.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Activity className="text-muted-foreground mb-4 h-12 w-12 opacity-20" />
              <h3 className="text-lg font-medium">No usage metrics available yet.</h3>
              <p className="text-muted-foreground mt-2 max-w-sm text-sm">
                Usage metrics will appear here once telemetry is configured.
              </p>
            </div>
          </CardContent>
        </Card>
      </TabsContent>

      <TabsContent value="keys" className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Key className="h-5 w-5" /> API Keys
            </CardTitle>
            <CardDescription>
              Manage API keys for programmatic access to your dashboard and agent publishing.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <ShieldAlert className="text-muted-foreground mb-4 h-12 w-12 opacity-20" />
              <h3 className="text-lg font-medium">No keys generated</h3>
              <p className="text-muted-foreground mt-2 max-w-sm text-sm">
                You currently don&apos;t have any active API keys. Use OAuth via GitHub for CLI
                interactions right now.
              </p>
              <Button className="mt-6" variant="outline" disabled>
                Generate New Key
              </Button>
            </div>
          </CardContent>
        </Card>
      </TabsContent>
    </Tabs>
  );
}
