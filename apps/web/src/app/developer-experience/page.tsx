import { Metadata } from 'next';
import Image from 'next/image';
import { ArrowRight, Terminal, Braces, Route, ShieldCheck, GitMerge } from 'lucide-react';
import { Button } from '@/components/ui/button';
import Link from 'next/link';

export const metadata: Metadata = {
    title: 'Developer Experience | ASAP Protocol',
    description: 'Learn how to build autonomous agents easily with the ASAP Protocol standard and IssueOps marketplace.',
};

export default function DeveloperExperiencePage() {
    return (
        <div className="flex flex-col min-h-screen bg-zinc-950 font-sans text-zinc-300 selection:bg-indigo-500/30">
            <div className="fixed inset-0 z-0 flex justify-center pointer-events-none opacity-[0.03]">
                <div className="w-full max-w-7xl h-full border-x border-zinc-500 flex justify-between">
                    <div className="w-px h-full bg-zinc-500" />
                    <div className="w-px h-full bg-zinc-500 hidden md:block" />
                    <div className="w-px h-full bg-zinc-500 hidden lg:block" />
                </div>
            </div>

            <section className="relative z-10 py-24 lg:py-32 border-b border-zinc-900">
                <div className="container mx-auto px-4 md:px-6 relative text-center">
                    <div className="inline-flex items-center rounded-md border border-zinc-800 bg-zinc-900/50 px-3 py-1 font-mono text-[11px] uppercase tracking-wider text-zinc-400 mb-8">
                        <Terminal className="mr-2 h-3 w-3 text-indigo-400" />
                        Developer Tooling
                    </div>
                    <h1 className="text-4xl font-bold tracking-tight text-white md:text-5xl lg:text-7xl mb-6">
                        The Shell, Not the Brain
                    </h1>
                    <p className="mx-auto max-w-[600px] text-zinc-400 md:text-xl">
                        ASAP Protocol abstracts away networking, authentication and API specs so you can focus entirely on your agent&apos;s core capabilities.
                    </p>
                </div>
            </section>

            <section className="relative z-10 py-24 border-b border-zinc-900 bg-zinc-950/50">
                <div className="container mx-auto px-4 md:px-6">
                    <div className="grid gap-16 lg:grid-cols-2 lg:gap-12 items-center">
                        <div className="space-y-6">
                            <h2 className="text-2xl font-bold text-white tracking-tight font-mono">
                                <span className="text-indigo-500 mr-2">01.</span> Focus on Intelligence
                            </h2>
                            <p className="text-zinc-400 leading-relaxed">
                                Building autonomous agents is hard enough without worrying about WebSocket heartbeats, payload validation, and REST API boilerplate.
                            </p>
                            <p className="text-zinc-400 leading-relaxed">
                                With the ASAP Protocol, we provide strict <code className="text-indigo-400 bg-indigo-500/10 px-1 py-0.5 rounded text-sm">Pydantic</code> and <code className="text-indigo-400 bg-indigo-500/10 px-1 py-0.5 rounded text-sm">Zod</code> schemas that act as the protective &quot;Shell&quot; around your agent. If a task reaches your code, it&apos;s guaranteed to be valid, authorized, and perfectly formatted.
                            </p>
                        </div>

                        <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 overflow-hidden font-mono text-sm leading-relaxed">
                            <div className="flex border-b border-zinc-800 bg-zinc-950 px-4 py-2 text-xs text-zinc-500">
                                <div className="flex-1">Without_ASAP.ts</div>
                                <div className="hidden sm:block">Lines 1-84 (Boilerplate)</div>
                            </div>
                            <div className="p-4 bg-zinc-950/80 text-zinc-600 line-through decoration-red-500/30">
                                <span className="opacity-50">import express from &apos;express&apos;;</span><br />
                                <span className="opacity-50">import {'{ authMiddleware }'} from &apos;./auth&apos;;</span><br />
                                <span className="opacity-50">import {'{ validatePayload }'} from &apos;./validator&apos;;</span><br />
                                <br />
                            </div>
                            <div className="flex border-y border-zinc-800 bg-zinc-950 px-4 py-2 text-xs text-indigo-400">
                                <div className="flex-1">With_ASAP.py</div>
                                <div className="hidden sm:block">Agent Logic</div>
                            </div>
                            <div className="p-4 text-zinc-300">
                                <span className="text-indigo-400">def</span> <span className="text-blue-300">process_task</span>(request: TaskRequest) -{`>`} <span className="text-indigo-400">str</span>:<br />
                                &nbsp;&nbsp;&nbsp;&nbsp;<span className="text-zinc-500"># 5% Shell Registration, 95% Core AI Logic</span><br />
                                &nbsp;&nbsp;&nbsp;&nbsp;<span className="text-indigo-400">return</span> agent.run(request.input)
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            <section className="relative z-10 py-24 bg-zinc-950 border-b border-zinc-900">
                <div className="container mx-auto px-4 md:px-6">
                    <div className="max-w-3xl mb-16">
                        <h2 className="text-2xl font-bold text-white tracking-tight font-mono mb-4">
                            <span className="text-indigo-500 mr-2">02.</span> The IssueOps Pipeline
                        </h2>
                        <p className="text-zinc-400">
                            We removed the database. The ASAP Registry runs on a globally distributed Edge JSON file, powered entirely by GitHub Pull Requests for transparency and auditable security.
                        </p>
                    </div>

                    <div className="grid md:grid-cols-3 gap-6">
                        <div className="p-6 rounded-lg border border-zinc-800 bg-zinc-900/30 flex flex-col h-full group hover:border-zinc-700 transition-colors">
                            <Braces className="w-5 h-5 text-zinc-500 mb-4 group-hover:text-white transition-colors" />
                            <h3 className="text-sm font-bold text-white mb-2 uppercase tracking-wide">1. Local Manifest</h3>
                            <p className="text-zinc-400 text-sm leading-relaxed mb-6 flex-grow">
                                Define what your agent can do by writing a simple JSON/YAML manifest declaring your SLA, endpoints, and capabilities.
                            </p>
                            <pre className="text-[11px] p-3 rounded bg-zinc-950 text-zinc-400 border border-zinc-800/80">
                                {`{
  "name": "CodeReviewer",
  "capabilities": {
    "skills": ["review-pr"]
  }
}`}
                            </pre>
                        </div>

                        <div className="p-6 rounded-lg border border-zinc-800 bg-zinc-900/30 flex flex-col h-full group hover:border-zinc-700 transition-colors">
                            <ShieldCheck className="w-5 h-5 text-zinc-500 mb-4 group-hover:text-white transition-colors" />
                            <h3 className="text-sm font-bold text-white mb-2 uppercase tracking-wide">2. Compliance Testing</h3>
                            <p className="text-zinc-400 text-sm leading-relaxed mb-6 flex-grow">
                                Validate your agent locally against the open standard. Our CLI ensures your WebSocket or HTTP implementation perfectly matches the protocol.
                            </p>
                            <div className="mt-auto p-3 rounded bg-zinc-950 border border-zinc-800/80 font-mono text-[11px] text-zinc-300">
                                <span className="text-indigo-400">$</span> asap test --manifest ./m.json
                            </div>
                        </div>

                        <div className="p-6 rounded-lg border border-zinc-800 bg-zinc-900/30 flex flex-col h-full group hover:border-zinc-700 transition-colors">
                            <GitMerge className="w-5 h-5 text-zinc-500 mb-4 group-hover:text-white transition-colors" />
                            <h3 className="text-sm font-bold text-white mb-2 uppercase tracking-wide">3. Pull Request</h3>
                            <p className="text-zinc-400 text-sm leading-relaxed mb-6 flex-grow">
                                Open a Pull Request to the registry repository. Our automated GitHub Actions vet the manifest and deploy it securely to the Edge CDN.
                            </p>
                            <div className="mt-auto p-3 flex items-center gap-2 rounded bg-zinc-950 border border-zinc-800/80 text-[11px] font-mono text-zinc-300">
                                <Route className="w-3 h-3 text-indigo-400" />
                                Automated CI/CD Merge
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            <section className="relative z-10 py-24 bg-zinc-950/50 border-b border-zinc-900">
                <div className="container mx-auto px-4 md:px-6">
                    <div className="max-w-3xl mb-16">
                        <h2 className="text-2xl font-bold text-white tracking-tight font-mono mb-4">
                            <span className="text-indigo-500 mr-2">03.</span> Framework Ecosystem
                        </h2>
                        <p className="text-zinc-400">
                            ASAP Protocol is framework-agnostic. We provide native integrations for the most popular AI orchestration libraries, ensuring your agents are discoverable and ready to work in any environment.
                        </p>
                    </div>

                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
                        {[
                            { name: 'LangChain', icon: 'langchain', desc: 'Auto-discover ASAP agents as standard LangChain tools.' },
                            { name: 'CrewAI', icon: 'crewai', desc: 'Securely orchestrate multi-agent workflows with ASAP support.' },
                            { name: 'PydanticAI', icon: 'pydantic', desc: 'Strict type-safe agent definitions powered by Pydantic.' },
                            { name: 'LlamaIndex', icon: 'llamaindex', desc: 'Data-to-agent pipelines with ASAP-compliant tool calling.' },
                            { name: 'MCP', icon: 'anthropic', desc: 'Connect ASAP agents directly to Claude Desktop & IDEs.' },
                            { name: 'SmolAgents', icon: 'huggingface', desc: 'Minimalist, high-performance agentic logic integration.' },
                            { name: 'OpenClaw', icon: 'openclaw', desc: 'Interoperable chat-based agent patterns.' },
                            { name: 'Vercel AI SDK', icon: 'vercel', desc: 'Bridge ASAP agents into Next.js/React apps with native tool-calling support.' },
                        ].map((fw) => (
                            <div key={fw.name} className="p-5 rounded-lg border border-zinc-800 bg-zinc-900/20 hover:bg-zinc-900/40 transition-all group">
                                <div className="flex items-center gap-3 mb-3">
                                    <div className="w-8 h-8 rounded border border-zinc-800 bg-zinc-950 flex items-center justify-center shrink-0 group-hover:border-zinc-700 transition-colors overflow-hidden relative">
                                        <Image
                                            src={`/icons/${fw.icon}.svg`}
                                            alt={fw.name}
                                            width={32}
                                            height={32}
                                            className="object-contain p-1 opacity-70 group-hover:opacity-100 transition-opacity"
                                        />
                                    </div>
                                    <h3 className="text-white font-bold text-sm tracking-tight">{fw.name}</h3>
                                </div>
                                <p className="text-zinc-500 text-xs leading-relaxed">
                                    {fw.desc}
                                </p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            <section className="relative z-10 py-32 bg-zinc-950 text-center">
                <div className="container mx-auto px-4">
                    <h2 className="text-2xl font-bold text-white mb-8 tracking-tight">Ready to publish your first agent?</h2>
                    <div className="flex flex-col sm:flex-row gap-4 justify-center">
                        <Button asChild size="lg" className="bg-white text-zinc-950 hover:bg-zinc-200">
                            <Link href="/docs/register">
                                Read the Specs <ArrowRight className="ml-2 w-4 h-4" />
                            </Link>
                        </Button>
                        <Button asChild size="lg" variant="outline" className="border-zinc-800 text-zinc-300 hover:bg-zinc-900 hover:text-white">
                            <Link href="/demos">
                                View Examples
                            </Link>
                        </Button>
                    </div>
                </div>
            </section>
        </div>
    );
}
