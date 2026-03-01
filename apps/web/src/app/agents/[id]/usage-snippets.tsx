'use client';

import type { RegistryAgent } from '@/types/registry';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Code2, Copy, Check } from 'lucide-react';
import { useState, useCallback } from 'react';

interface UsageSnippetsProps {
    agentId: string;
    agent: RegistryAgent;
}

const firstSkillId = (agent: RegistryAgent): string =>
    Array.isArray(agent.capabilities?.skills) && agent.capabilities.skills.length > 0
        ? (agent.capabilities.skills[0] as { id: string }).id
        : 'example-skill';

const agentSlug = (id: string) => id?.split(':').pop() ?? 'agent';

function openclawSnippetText(agentId: string, firstSkill: string): string {
    return `# 1. Install the ASAP skill
npx clawskills@latest install asap-openclaw-skill

# 2. Add to openclaw.json (allow asap_invoke and use this agent)
{
  "agents": {
    "list": [
      {
        "id": "main",
        "tools": {
          "allow": ["asap_invoke"]
        }
      }
    ]
  }
}

# 3. Call asap_invoke with urn="${agentId}", skill="${firstSkill}", input={ ... }`;
}

export function UsageSnippets({ agentId, agent }: UsageSnippetsProps) {
    const [openclawCopied, setOpenclawCopied] = useState(false);

    const copyOpenclawSnippet = useCallback(async () => {
        const text = openclawSnippetText(agentId, firstSkillId(agent));
        await navigator.clipboard.writeText(text);
        setOpenclawCopied(true);
        setTimeout(() => setOpenclawCopied(false), 2000);
    }, [agentId, agent]);
    return (
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
                    <TabsList className="flex flex-wrap h-auto w-full justify-start gap-1 p-1">
                        <TabsTrigger value="node" className="flex-grow sm:flex-grow-0">Node.js</TabsTrigger>
                        <TabsTrigger value="langchain">LangChain</TabsTrigger>
                        <TabsTrigger value="llamaindex">LlamaIndex</TabsTrigger>
                        <TabsTrigger value="crewai">CrewAI</TabsTrigger>
                        <TabsTrigger value="smolagents">SmolAgents</TabsTrigger>
                        <TabsTrigger value="pydanticai">PydanticAI</TabsTrigger>
                        <TabsTrigger value="openclaw">OpenClaw</TabsTrigger>
                        <TabsTrigger value="mcp">MCP</TabsTrigger>
                    </TabsList>

                    <TabsContent value="node" className="mt-4">
                        <div className="group relative rounded-md bg-zinc-950 p-4 font-mono text-sm text-zinc-300 border border-zinc-800 overflow-x-auto">
                            <pre className="leading-relaxed">
                                <span className="text-zinc-500"># 1. Install the client</span>{'\n'}
                                <span className="text-indigo-400">npm</span> install @asap/client{'\n\n'}
                                <span className="text-zinc-500"># 2. Connect and route requests</span>{'\n'}
                                <span className="text-purple-400">import</span> {'{'} AsapClient {'}'} <span className="text-purple-400">from</span> <span className="text-emerald-300">&apos;@asap/client&apos;</span>;{'\n\n'}
                                <span className="text-purple-400">const</span> client = <span className="text-purple-400">new</span> AsapClient();{'\n'}
                                <span className="text-purple-400">await</span> client.connect(<span className="text-emerald-300">&apos;{agentId}&apos;</span>);{'\n\n'}
                                <span className="text-purple-400">const</span> response = <span className="text-purple-400">await</span> client.sendTask({'{'}{'\n'}
                                {'  '}skill: <span className="text-emerald-300">&apos;{firstSkillId(agent)}&apos;</span>,{'\n'}
                                {'  '}input: {'{ /* payload */ }'}{'\n'}
                                {'}'});
                            </pre>
                        </div>
                    </TabsContent>

                    <TabsContent value="langchain" className="mt-4">
                        <div className="group relative rounded-md bg-zinc-950 p-4 font-mono text-sm text-zinc-300 border border-zinc-800 overflow-x-auto">
                            <pre className="leading-relaxed">
                                <span className="text-zinc-500"># 1. Install the provider</span>{'\n'}
                                <span className="text-indigo-400">pip</span> install <span className="text-emerald-300">&quot;asap-protocol[langchain]&quot;</span>{'\n\n'}
                                <span className="text-zinc-500"># 2. Auto-discover tools</span>{'\n'}
                                <span className="text-purple-400">from</span> asap.integrations.langchain <span className="text-purple-400">import</span> AsapToolProvider{'\n\n'}
                                provider = AsapToolProvider(){'\n'}
                                tools = provider.get_tools(agent_id=<span className="text-emerald-300">&quot;{agentId}&quot;</span>){'\n\n'}
                                <span className="text-zinc-500"># 3. Use with agent</span>{'\n'}
                                agent = initialize_agent(tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION)
                            </pre>
                        </div>
                    </TabsContent>

                    <TabsContent value="llamaindex" className="mt-4">
                        <div className="group relative rounded-md bg-zinc-950 p-4 font-mono text-sm text-zinc-300 border border-zinc-800 overflow-x-auto">
                            <pre className="leading-relaxed">
                                <span className="text-zinc-500"># 1. Install the provider</span>{'\n'}
                                <span className="text-indigo-400">pip</span> install <span className="text-emerald-300">&quot;asap-protocol[llamaindex]&quot;</span>{'\n\n'}
                                <span className="text-zinc-500"># 2. Import and use LlamaIndexAsapTool</span>{'\n'}
                                <span className="text-purple-400">from</span> asap.integrations.llamaindex <span className="text-purple-400">import</span> LlamaIndexAsapTool{'\n\n'}
                                asap_tool = LlamaIndexAsapTool(<span className="text-emerald-300">&quot;{agentId}&quot;</span>){'\n'}
                                tools = [asap_tool]{'\n\n'}
                                <span className="text-zinc-500"># 3. Use with LlamaIndex agent / query engine</span>{'\n'}
                                response = index.as_query_engine(tools=tools).query(<span className="text-emerald-300">&quot;Your query&quot;</span>)
                            </pre>
                        </div>
                    </TabsContent>

                    <TabsContent value="crewai" className="mt-4">
                        <div className="group relative rounded-md bg-zinc-950 p-4 font-mono text-sm text-zinc-300 border border-zinc-800 overflow-x-auto">
                            <pre className="leading-relaxed">
                                <span className="text-zinc-500"># 1. Install the provider</span>{'\n'}
                                <span className="text-indigo-400">pip</span> install <span className="text-emerald-300">&quot;asap-protocol[crewai]&quot;</span>{'\n\n'}
                                <span className="text-zinc-500"># 2. Import and use</span>{'\n'}
                                <span className="text-purple-400">from</span> asap.integrations.crewai <span className="text-purple-400">import</span> get_crewai_tools{'\n\n'}
                                asap_tools = get_crewai_tools(agent_id=<span className="text-emerald-300">&quot;{agentId}&quot;</span>){'\n\n'}
                                researcher = Agent({'\n'}
                                {'    '}role=<span className="text-emerald-300">&apos;Researcher&apos;</span>,{'\n'}
                                {'    '}tools=asap_tools{'\n'}
                                )
                            </pre>
                        </div>
                    </TabsContent>

                    <TabsContent value="smolagents" className="mt-4">
                        <div className="group relative rounded-md bg-zinc-950 p-4 font-mono text-sm text-zinc-300 border border-zinc-800 overflow-x-auto">
                            <pre className="leading-relaxed">
                                <span className="text-zinc-500"># 1. Install the provider</span>{'\n'}
                                <span className="text-indigo-400">pip</span> install <span className="text-emerald-300">&quot;asap-protocol[smolagents]&quot;</span>{'\n\n'}
                                <span className="text-zinc-500"># 2. Import and use SmolAgentsAsapTool</span>{'\n'}
                                <span className="text-purple-400">from</span> asap.integrations.smolagents <span className="text-purple-400">import</span> SmolAgentsAsapTool{'\n\n'}
                                asap_tool = SmolAgentsAsapTool(<span className="text-emerald-300">&quot;{agentId}&quot;</span>){'\n'}
                                agent = Agent(tools=[asap_tool], ...)
                            </pre>
                        </div>
                    </TabsContent>

                    <TabsContent value="pydanticai" className="mt-4">
                        <div className="group relative rounded-md bg-zinc-950 p-4 font-mono text-sm text-zinc-300 border border-zinc-800 overflow-x-auto">
                            <pre className="leading-relaxed">
                                <span className="text-zinc-500"># 1. Install the provider</span>{'\n'}
                                <span className="text-indigo-400">pip</span> install <span className="text-emerald-300">&quot;asap-protocol[pydanticai]&quot;</span>{'\n\n'}
                                <span className="text-zinc-500"># 2. Connect via PydanticAI</span>{'\n'}
                                <span className="text-purple-400">from</span> pydantic_ai <span className="text-purple-400">import</span> Agent{'\n'}
                                <span className="text-purple-400">from</span> asap.integrations.pydanticai <span className="text-purple-400">import</span> register_asap_tools{'\n\n'}
                                agent = Agent(model=<span className="text-emerald-300">&apos;openai:gpt-4o&apos;</span>){'\n'}
                                register_asap_tools(agent, agent_id=<span className="text-emerald-300">&quot;{agentId}&quot;</span>){'\n\n'}
                                result = agent.run_sync(<span className="text-emerald-300">&apos;Use the agent to solve this task&apos;</span>)
                            </pre>
                        </div>
                    </TabsContent>

                    <TabsContent value="openclaw" className="mt-4">
                        <div className="group relative rounded-md bg-zinc-950 p-4 font-mono text-sm text-zinc-300 border border-zinc-800 overflow-x-auto">
                            <Button
                                variant="ghost"
                                size="icon"
                                className="absolute right-2 top-2 h-8 w-8 text-zinc-400 hover:text-zinc-200"
                                onClick={copyOpenclawSnippet}
                                aria-label={openclawCopied ? 'Copied' : 'Copy snippet'}
                            >
                                {openclawCopied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                            </Button>
                            <pre className="leading-relaxed pr-10">
                                <span className="text-zinc-500"># 1. Install the ASAP skill</span>{'\n'}
                                <span className="text-indigo-400">npx</span> clawskills@latest install asap-openclaw-skill{'\n\n'}
                                <span className="text-zinc-500"># 2. Add to openclaw.json (allow asap_invoke and use this agent)</span>{'\n'}
                                {'{'}{'\n'}
                                {'  '}<span className="text-emerald-300">&quot;agents&quot;</span>: {'{'}{'\n'}
                                {'    '}<span className="text-emerald-300">&quot;list&quot;</span>: [{'\n'}
                                {'      '}<span className="text-emerald-300">&quot;id&quot;</span>: <span className="text-emerald-300">&quot;main&quot;</span>,{'\n'}
                                {'      '}<span className="text-emerald-300">&quot;tools&quot;</span>: {'{'}{'\n'}
                                {'        '}<span className="text-emerald-300">&quot;allow&quot;</span>: [<span className="text-emerald-300">&quot;asap_invoke&quot;</span>]{'\n'}
                                {'      '}{'}'}{'\n'}
                                {'    '}]{'\n'}
                                {'  '}{'}'}{'\n'}
                                {'}'}{'\n\n'}
                                <span className="text-zinc-500"># 3. Call asap_invoke with urn=&quot;{agentId}&quot;, skill=&quot;{firstSkillId(agent)}&quot;, input= {'{'} ... {'}'}</span>
                            </pre>
                        </div>
                    </TabsContent>

                    <TabsContent value="mcp" className="mt-4">
                        <div className="group relative rounded-md bg-zinc-950 p-4 font-mono text-sm text-zinc-300 border border-zinc-800 overflow-x-auto">
                            <pre className="leading-relaxed">
                                <span className="text-zinc-500"># Use ASAP Protocol as an MCP Server (e.g. Claude Desktop)</span>{'\n'}
                                <span className="text-zinc-500"># Add to your claude_desktop_config.json:</span>{'\n'}
                                {'{'}{'\n'}
                                {'  '}<span className="text-emerald-300">&quot;mcpServers&quot;</span>: {'{'}{'\n'}
                                {'    '}<span className="text-emerald-300">&quot;asap-agent-{agentSlug(agentId)}&quot;</span>: {'{'}{'\n'}
                                {'      '}<span className="text-emerald-300">&quot;command&quot;</span>: <span className="text-emerald-300">&quot;uvx&quot;</span>,{'\n'}
                                {'      '}<span className="text-emerald-300">&quot;args&quot;</span>: [<span className="text-emerald-300">&quot;asap-protocol&quot;</span>, <span className="text-emerald-300">&quot;mcp&quot;</span>, <span className="text-emerald-300">&quot;--agent-id&quot;</span>, <span className="text-emerald-300">&quot;{agentId}&quot;</span>]{'\n'}
                                {'    '}{'}'}{'\n'}
                                {'  '}{'}'}{'\n'}
                                {'}'}
                            </pre>
                        </div>
                    </TabsContent>
                </Tabs>
            </CardContent>
        </Card>
    );
}
