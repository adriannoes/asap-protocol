import Link from 'next/link';
import { ArrowLeft, TerminalSquare, Rss, ArrowRightLeft, Terminal } from 'lucide-react';
import { Metadata } from 'next';

export const metadata: Metadata = {
    title: 'Protocol Demos | ASAP Protocol',
    description: 'Visual technical showcases of the ASAP Protocol architecture in action.',
};

export default function DemosPage() {
    return (
        <main className="flex flex-col min-h-screen bg-zinc-950 font-sans text-zinc-300 selection:bg-indigo-500/30">
            <div className="fixed inset-0 z-0 flex justify-center pointer-events-none opacity-[0.03]">
                <div className="w-full max-w-7xl h-full border-x border-zinc-500 flex justify-between">
                    <div className="w-px h-full bg-zinc-500" />
                    <div className="w-px h-full bg-zinc-500 hidden md:block" />
                    <div className="w-px h-full bg-zinc-500 hidden lg:block" />
                </div>
            </div>

            <div className="container relative z-10 mx-auto px-4 py-16 sm:px-6 lg:px-8">
                <div className="mb-8">
                    <Link
                        href="/"
                        className="group flex items-center text-sm font-mono text-zinc-500 transition-colors hover:text-white"
                    >
                        <ArrowLeft className="mr-2 h-4 w-4 transition-transform group-hover:-translate-x-1" />
                        cd ..
                    </Link>
                </div>

                <header className="mb-24 max-w-3xl">
                    <div className="inline-flex items-center rounded-md border border-zinc-800 bg-zinc-900/50 px-3 py-1 font-mono text-[11px] uppercase tracking-wider text-zinc-400 mb-8">
                        <Terminal className="mr-2 h-3 w-3 text-cyan-400" />
                        Protocol Showcase
                    </div>
                    <h1 className="mb-6 text-4xl font-bold tracking-tight text-white sm:text-5xl lg:text-7xl">
                        Execution in Action
                    </h1>
                    <p className="text-xl text-zinc-400">
                        See the ASAP Protocol in action. Explore how developers integrate agents over JSON-RPC 2.0 — with version negotiation, scoped capabilities, and streaming responses via WebSockets or Server-Sent Events.
                    </p>
                </header>

                <div className="space-y-32">

                    <section>
                        <div className="mb-12 flex items-center gap-4 border-b border-zinc-900 pb-4">
                            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-zinc-900 border border-zinc-800">
                                <ArrowRightLeft className="h-5 w-5 text-indigo-400" />
                            </div>
                            <div>
                                <h2 className="text-2xl font-bold tracking-tight text-white font-mono">1. The <code>.process</code> Command</h2>
                                <p className="text-zinc-500 font-mono text-sm">Universal JSON-RPC 2.0 orchestration over HTTP or WebSocket.</p>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 xl:grid-cols-2 gap-12 items-center">
                            <div className="space-y-6 text-zinc-400 leading-relaxed text-lg">
                                <p>
                                    Instead of learning a different REST API wrapper for every LLM or agent, ASAP normalizes the invocation surface around JSON-RPC 2.0.
                                </p>
                                <p>
                                    Send a single envelope to <code>POST /asap</code> — or open a WebSocket for bidirectional flows — and the agent immediately starts streaming state. Version negotiation via the <code>ASAP-Version</code> header keeps clients and servers compatible across releases.
                                </p>
                            </div>

                            <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 overflow-hidden font-mono text-[13px] leading-relaxed w-full">
                                <div className="flex border-b border-zinc-800 bg-zinc-950 px-4 py-2 text-xs text-zinc-500">
                                    <div className="flex-1">client.ts</div>
                                </div>
                                <div className="p-4 bg-zinc-950/80 text-zinc-300 overflow-x-auto whitespace-pre">
                                    <span className="text-indigo-400">const</span> <span className="text-blue-300">ws</span> = <span className="text-indigo-400">new</span> WebSocket(<span className="text-green-300">&apos;wss://agent.example.com/asap&apos;</span>);<br />
                                    <br />
                                    ws.send(JSON.stringify({'{'}<br />
                                    &nbsp;&nbsp;action: <span className="text-green-300">&quot;.process&quot;</span>,<br />
                                    &nbsp;&nbsp;input: {'{'}<br />
                                    &nbsp;&nbsp;&nbsp;&nbsp;prompt: <span className="text-green-300">&quot;Summarize this PR...&quot;</span>,<br />
                                    &nbsp;&nbsp;&nbsp;&nbsp;context: <span className="text-green-300">&quot;github.com/pulls/1&quot;</span><br />
                                    &nbsp;&nbsp;{'}'}<br />
                                    {'}'}));<br />
                                    <br />
                                    <span className="text-cyan-400">{'<-'}</span> {'{'} <span className="text-indigo-300">&quot;type&quot;</span>: <span className="text-green-300">&quot;lifecycle&quot;</span>, <span className="text-indigo-300">&quot;status&quot;</span>: <span className="text-green-300">&quot;started&quot;</span> {'}'}<br />
                                    <span className="text-cyan-400">{'<-'}</span> {'{'} <span className="text-indigo-300">&quot;type&quot;</span>: <span className="text-green-300">&quot;lifecycle&quot;</span>, <span className="text-indigo-300">&quot;status&quot;</span>: <span className="text-green-300">&quot;processing&quot;</span> {'}'}<br />
                                    <span className="text-purple-400">{'<-'}</span> {'{'} <span className="text-indigo-300">&quot;type&quot;</span>: <span className="text-green-300">&quot;output&quot;</span>, <span className="text-indigo-300">&quot;data&quot;</span>: {'{'} <span className="text-indigo-300">&quot;result&quot;</span>: <span className="text-green-300">&quot;...&quot;</span> {'}'} {'}'}
                                </div>
                            </div>
                        </div>
                    </section>

                    <section>
                        <div className="mb-12 flex items-center gap-4 border-b border-zinc-900 pb-4">
                            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-zinc-900 border border-zinc-800">
                                <TerminalSquare className="h-5 w-5 text-cyan-400" />
                            </div>
                            <div>
                                <h2 className="text-2xl font-bold tracking-tight text-white font-mono">2. Strict Schema validation</h2>
                                <p className="text-zinc-500 font-mono text-sm">Zero guesswork with capability schemas and Zod.</p>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 xl:grid-cols-2 gap-12 items-center">
                            <div className="order-2 xl:order-1 rounded-lg border border-zinc-800 bg-zinc-900/50 overflow-hidden font-mono text-[13px] leading-relaxed w-full">
                                <div className="flex border-b border-zinc-800 bg-zinc-950 px-4 py-2 text-xs text-zinc-500">
                                    <div className="flex-1">validator.ts</div>
                                </div>
                                <div className="p-4 bg-zinc-950/80 text-zinc-300 overflow-x-auto whitespace-pre">
                                    <span className="text-indigo-400">import</span> {'{'} z {'}'} <span className="text-indigo-400">from</span> <span className="text-green-300">&quot;zod&quot;</span>;<br />
                                    <br />
                                    <span className="text-indigo-400">const</span> InputSchema = z.object({'{'}<br />
                                    &nbsp;&nbsp;repository: z.string().url(),<br />
                                    &nbsp;&nbsp;branch: z.string().optional()<br />
                                    {'}'});<br />
                                    <br />
                                    <span className="text-indigo-400">const</span> payload = {'{'}<br />
                                    &nbsp;&nbsp;repository: <span className="text-red-300">&quot;not-a-url&quot;</span>,<br />
                                    {'}'};<br />
                                    <br />
                                    <span className="text-indigo-400">const</span> valid = InputSchema.safeParse(payload);<br />
                                    <br />
                                    <span className="text-red-400">if</span> (!valid.success) {'{'}<br />
                                    &nbsp;&nbsp;console.error(<span className="text-red-300">&quot;Agent Rejected: Invalid Input URLs&quot;</span>);<br />
                                    {'}'}
                                </div>
                            </div>
                            <div className="order-1 xl:order-2 space-y-6 text-zinc-400 leading-relaxed text-lg">
                                <p>
                                    Every ASAP agent publishes a strict JSON Schema inside its registry manifest.
                                </p>
                                <p>
                                    Because the orchestration data layer maps 1:1, developers can instantly wrap requests in Zod or TypeScript types, catching invalid inputs locally before they ever hit the agent&apos;s network boundaries.
                                </p>
                                <p>
                                    Since v2.2, every capability publishes its own input schema plus optional constraint operators (<code>max</code>, <code>min</code>, <code>in</code>, <code>not_in</code>) — so consumers know exactly what they&apos;re granting before the agent ever acts.
                                </p>
                            </div>
                        </div>
                    </section>

                    <section>
                        <div className="mb-12 flex items-center gap-4 border-b border-zinc-900 pb-4">
                            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-zinc-900 border border-zinc-800">
                                <Rss className="h-5 w-5 text-purple-400" />
                            </div>
                            <div>
                                <h2 className="text-2xl font-bold tracking-tight text-white font-mono">3. Memory Snapshots</h2>
                                <p className="text-zinc-500 font-mono text-sm">Complete observability into thought processes.</p>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 xl:grid-cols-2 gap-12 items-center">
                            <div className="space-y-6 text-zinc-400 leading-relaxed text-lg">
                                <p>
                                    The protocol standardizes incremental updates so long-running tasks — like recursive Code Reviewers — never leave you waiting in the dark.
                                </p>
                                <p>
                                    Subscribe to a WebSocket for bidirectional <code>memory_snapshot</code> events, or hit <code>POST /asap/stream</code> with <code>Accept: text/event-stream</code> to consume <code>TaskStream</code> chunks over Server-Sent Events. Either way, you build rich, dynamic UIs that update as the agent thinks.
                                </p>
                            </div>

                            <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 overflow-hidden font-mono text-[13px] leading-relaxed w-full">
                                <div className="flex border-b border-zinc-800 bg-zinc-950 px-4 py-2 text-xs text-zinc-500">
                                    <div className="flex-1">WebSocket Stream</div>
                                </div>
                                <div className="p-4 bg-zinc-950/80 text-zinc-300 overflow-x-auto whitespace-pre">
                                    <span className="text-zinc-500">{'<- WS Event Received'}</span><br />
                                    {'{'}<br />
                                    &nbsp;&nbsp;<span className="text-indigo-300">&quot;type&quot;</span>: <span className="text-purple-300">&quot;memory_snapshot&quot;</span>,<br />
                                    &nbsp;&nbsp;<span className="text-indigo-300">&quot;data&quot;</span>: {'{'}<br />
                                    &nbsp;&nbsp;&nbsp;&nbsp;<span className="text-indigo-300">&quot;thought&quot;</span>: <span className="text-green-300">&quot;I found a bug in line 42. Calling AST parser...&quot;</span>,<br />
                                    &nbsp;&nbsp;&nbsp;&nbsp;<span className="text-indigo-300">&quot;tool_calls&quot;</span>: [<span className="text-green-300">&quot;parse_typescript_ast&quot;</span>],<br />
                                    &nbsp;&nbsp;&nbsp;&nbsp;<span className="text-indigo-300">&quot;internal_logs&quot;</span>: [<br />
                                    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span className="text-zinc-400">&quot;[INFO] Parsed 240 Nodes.&quot;</span><br />
                                    &nbsp;&nbsp;&nbsp;&nbsp;]<br />
                                    &nbsp;&nbsp;{'}'}<br />
                                    {'}'}<br />
                                    <br />
                                </div>
                            </div>
                        </div>
                    </section>

                </div>

                <div className="mt-32 pt-16 border-t border-zinc-900 text-center relative z-10">
                    <h2 className="mb-6 text-3xl font-bold tracking-tight text-white">
                        Ready to start building?
                    </h2>
                    <p className="mb-8 text-xl text-zinc-400 max-w-2xl mx-auto">
                        Dive into our repository to see fully functional examples of ASAP agents built in Python, with reference integrations for LangChain, CrewAI, PydanticAI, LlamaIndex and more.
                    </p>
                    <div className="flex items-center justify-center gap-4">
                        <Link
                            href="https://github.com/adriannoes/asap-protocol/tree/main/src/asap/examples"
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex h-12 items-center justify-center rounded-md bg-white px-8 text-sm font-medium text-zinc-950 transition-colors hover:bg-zinc-200"
                        >
                            View Code Examples
                        </Link>
                        <Link
                            href="/browse"
                            className="inline-flex h-12 items-center justify-center rounded-md border border-zinc-700 bg-transparent px-8 text-sm font-medium text-zinc-300 hover:text-white transition-colors hover:bg-zinc-800"
                        >
                            Browse Registry
                        </Link>
                    </div>
                </div>

            </div>
        </main>
    );
}
