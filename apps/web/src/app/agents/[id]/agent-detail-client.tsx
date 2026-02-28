import type { RegistryAgent } from '@/types/registry';
import { isAllowedExternalUrl } from '@/lib/url-validator';
import { AgentStatusBadge } from '@/components/agent/agent-status-badge';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { ArrowLeft, ExternalLink, ShieldAlert, ShieldCheck, TerminalSquare } from 'lucide-react';
import Link from 'next/link';
import { Code2 } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

interface AgentDetailClientProps {
    agent: RegistryAgent;
    isRevoked?: boolean;
}

function safeAuthHref(url: unknown): string {
    if (typeof url !== 'string') return '#';
    return isAllowedExternalUrl(url).valid ? url : '#';
}

export function AgentDetailClient({ agent, isRevoked }: AgentDetailClientProps) {
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
                        <div className="flex items-center gap-3">
                            <h1 className="text-3xl font-bold tracking-tight">{agent.name}</h1>
                            {isRevoked && (
                                <Badge variant="destructive" className="text-sm px-2 py-0.5">
                                    Revoked
                                </Badge>
                            )}
                        </div>
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
                            {agentEndpoint && <AgentStatusBadge endpoint={agentEndpoint} skipReachabilityCheck={agent.online_check === false} size="default" />}
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
                                        <a href={safeAuthHref(agent.repository_url)} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1">
                                            <ExternalLink className="w-3 h-3" /> Repository
                                        </a>
                                    </Button>
                                )}
                                {agent.documentation_url && (
                                    <Button variant="outline" size="sm" className="text-xs" asChild>
                                        <a href={safeAuthHref(agent.documentation_url)} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1">
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
                    {/* Developer Quick Start / Usage Snippets */}
                    <Card className="border-indigo-500/20 shadow-sm shadow-indigo-500/5">
                        <CardHeader className="pb-3">
                            <CardTitle className="text-lg flex items-center gap-2">
                                <Code2 className="w-5 h-5 text-indigo-400" />
                                Usage Snippets
                            </CardTitle>
                            <CardDescription>
                                Connect to this agent using your favorite framework.
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <Tabs defaultValue="node" className="w-full">
                                <TabsList className="grid w-full grid-cols-2 md:grid-cols-5 h-auto md:h-10">
                                    <TabsTrigger value="node">Node.js</TabsTrigger>
                                    <TabsTrigger value="langchain">LangChain</TabsTrigger>
                                    <TabsTrigger value="crewai">CrewAI</TabsTrigger>
                                    <TabsTrigger value="pydanticai">PydanticAI</TabsTrigger>
                                    <TabsTrigger value="mcp">MCP</TabsTrigger>
                                </TabsList>

                                {/* Node.js Snippet */}
                                <TabsContent value="node" className="mt-4">
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
                                </TabsContent>

                                {/* LangChain Snippet */}
                                <TabsContent value="langchain" className="mt-4">
                                    <div className="group relative rounded-md bg-zinc-950 p-4 font-mono text-sm text-zinc-300 border border-zinc-800 overflow-x-auto">
                                        <pre className="leading-relaxed">
                                            <span className="text-zinc-500"># 1. Install the provider</span>{'\n'}
                                            <span className="text-indigo-400">pip</span> install <span className="text-emerald-300">&quot;asap-protocol[langchain]&quot;</span>{'\n\n'}
                                            <span className="text-zinc-500"># 2. Auto-discover tools</span>{'\n'}
                                            <span className="text-purple-400">from</span> asap.integrations.langchain <span className="text-purple-400">import</span> AsapToolProvider{'\n\n'}
                                            provider = AsapToolProvider(){'\n'}
                                            tools = provider.get_tools(agent_id=<span className="text-emerald-300">&quot;{agent.id}&quot;</span>){'\n\n'}
                                            <span className="text-zinc-500"># 3. Use with agent</span>{'\n'}
                                            agent = initialize_agent(tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION)
                                        </pre>
                                    </div>
                                </TabsContent>

                                {/* CrewAI Snippet */}
                                <TabsContent value="crewai" className="mt-4">
                                    <div className="group relative rounded-md bg-zinc-950 p-4 font-mono text-sm text-zinc-300 border border-zinc-800 overflow-x-auto">
                                        <pre className="leading-relaxed">
                                            <span className="text-zinc-500"># 1. Install the provider</span>{'\n'}
                                            <span className="text-indigo-400">pip</span> install <span className="text-emerald-300">&quot;asap-protocol[crewai]&quot;</span>{'\n\n'}
                                            <span className="text-zinc-500"># 2. Import and use</span>{'\n'}
                                            <span className="text-purple-400">from</span> asap.integrations.crewai <span className="text-purple-400">import</span> get_crewai_tools{'\n\n'}
                                            asap_tools = get_crewai_tools(agent_id=<span className="text-emerald-300">&quot;{agent.id}&quot;</span>){'\n\n'}
                                            researcher = Agent({'\n'}
                                            {'    '}role=<span className="text-emerald-300">&apos;Researcher&apos;</span>,{'\n'}
                                            {'    '}tools=asap_tools{'\n'}
                                            )
                                        </pre>
                                    </div>
                                </TabsContent>

                                {/* PydanticAI Snippet */}
                                <TabsContent value="pydanticai" className="mt-4">
                                    <div className="group relative rounded-md bg-zinc-950 p-4 font-mono text-sm text-zinc-300 border border-zinc-800 overflow-x-auto">
                                        <pre className="leading-relaxed">
                                            <span className="text-zinc-500"># 1. Install the provider</span>{'\n'}
                                            <span className="text-indigo-400">pip</span> install <span className="text-emerald-300">&quot;asap-protocol[pydanticai]&quot;</span>{'\n\n'}
                                            <span className="text-zinc-500"># 2. Connect via PydanticAI</span>{'\n'}
                                            <span className="text-purple-400">from</span> pydantic_ai <span className="text-purple-400">import</span> Agent{'\n'}
                                            <span className="text-purple-400">from</span> asap.integrations.pydanticai <span className="text-purple-400">import</span> register_asap_tools{'\n\n'}
                                            agent = Agent(model=<span className="text-emerald-300">&apos;openai:gpt-4o&apos;</span>){'\n'}
                                            register_asap_tools(agent, agent_id=<span className="text-emerald-300">&quot;{agent.id}&quot;</span>){'\n\n'}
                                            result = agent.run_sync(<span className="text-emerald-300">&apos;Use the agent to solve this task&apos;</span>)
                                        </pre>
                                    </div>
                                </TabsContent>

                                {/* MCP Snippet */}
                                <TabsContent value="mcp" className="mt-4">
                                    <div className="group relative rounded-md bg-zinc-950 p-4 font-mono text-sm text-zinc-300 border border-zinc-800 overflow-x-auto">
                                        <pre className="leading-relaxed">
                                            <span className="text-zinc-500"># Use ASAP Protocol as an MCP Server (e.g. Claude Desktop)</span>{'\n'}
                                            <span className="text-zinc-500"># Add to your claude_desktop_config.json:</span>{'\n'}
                                            {'{'}{'\n'}
                                            {'  '}<span className="text-emerald-300">&quot;mcpServers&quot;</span>: {'{'}{'\n'}
                                            {'    '}<span className="text-emerald-300">&quot;asap-agent-{agent.id?.split(':').pop()}&quot;</span>: {'{'}{'\n'}
                                            {'      '}<span className="text-emerald-300">&quot;command&quot;</span>: <span className="text-emerald-300">&quot;uvx&quot;</span>,{'\n'}
                                            {'      '}<span className="text-emerald-300">&quot;args&quot;</span>: [<span className="text-emerald-300">&quot;asap-protocol&quot;</span>, <span className="text-emerald-300">&quot;mcp&quot;</span>, <span className="text-emerald-300">&quot;--agent-id&quot;</span>, <span className="text-emerald-300">&quot;{agent.id}&quot;</span>]{'\n'}
                                            {'    '}{'}'}{'\n'}
                                            {'  '}{'}'}{'\n'}
                                            {'}'}
                                        </pre>
                                    </div>
                                </TabsContent>
                            </Tabs>
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
