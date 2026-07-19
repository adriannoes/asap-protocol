import { Metadata } from 'next';
import { ArrowRight, BookOpen, ShieldCheck, GitPullRequest, Code2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import Link from 'next/link';
import { CanvasBg } from '@/components/ui/canvas-bg';

export const metadata: Metadata = {
    title: 'Register Agent Specs | ASAP Protocol',
    description: 'Documentation on how to define your agent manifest and register it in the ASAP Protocol marketplace.',
};

export const dynamic = 'force-static';

export default function DocsRegisterPage() {
    return (
        <div className="relative flex flex-col min-h-screen font-sans text-zinc-300 selection:bg-indigo-500/30 overflow-hidden">
            <CanvasBg />
            <div className="fixed inset-0 z-0 flex justify-center pointer-events-none opacity-[0.03]">
                <div className="w-full max-w-7xl h-full border-x border-zinc-500">
                    <div className="w-px h-full bg-zinc-500 ml-[33%] absolute left-0 hidden md:block" />
                    <div className="w-px h-full bg-zinc-500 mr-[33%] absolute right-0 hidden lg:block" />
                </div>
            </div>

            <section className="relative z-10 py-20 border-b border-zinc-900 bg-zinc-950">
                <div className="container mx-auto px-4 max-w-4xl relative">
                    <div className="inline-flex items-center rounded-md border border-zinc-800 bg-zinc-900/50 px-3 py-1 font-mono text-[11px] uppercase tracking-wider text-zinc-400 mb-6">
                        <BookOpen className="mr-2 h-3 w-3 text-indigo-400" />
                        Documentation / Specs
                    </div>
                    <h1 className="text-3xl font-bold tracking-tight text-white md:text-5xl mb-4">
                        Register Your Agent
                    </h1>
                    <p className="text-zinc-400 text-lg leading-relaxed">
                        To join the ASAP Protocol marketplace, your agent must expose a standard manifest and be registered in the <strong className="text-white">Lite Registry</strong>. Follow the specs below to prepare your agent and publish it via IssueOps.
                    </p>
                </div>
            </section>

            <section className="relative z-10 py-16">
                <div className="container mx-auto px-4 max-w-4xl space-y-16">

                    <div className="space-y-6">
                        <div className="flex items-center gap-4">
                            <div className="flex items-center justify-center w-8 h-8 rounded-full bg-indigo-500/10 text-indigo-400 font-bold border border-indigo-500/20">
                                1
                            </div>
                            <h2 className="text-2xl font-bold text-white">Define the Agent Manifest</h2>
                        </div>
                        <p className="text-zinc-400 leading-relaxed">
                            The manifest describes your agent and its capabilities. According to the ASAP Specification, your server must expose it (usually at <code className="text-indigo-400 bg-indigo-500/10 px-1.5 py-0.5 rounded text-sm font-mono">/.well-known/asap/manifest.json</code>). Here is an exact snippet from our official tutorials on how to define it via the Python SDK:
                        </p>

                        <div className="rounded-xl overflow-hidden border border-zinc-800 bg-zinc-900">
                            <div className="flex items-center justify-between px-4 py-2 border-b border-zinc-800 bg-zinc-950">
                                <div className="flex items-center gap-2">
                                    <Code2 className="w-4 h-4 text-zinc-500" />
                                    <span className="text-xs font-mono text-zinc-400">my_echo_agent.py</span>
                                </div>
                            </div>
                            <pre className="p-6 text-sm font-mono text-zinc-300 overflow-x-auto leading-relaxed">
                                <code>{`from asap.models.entities import Capability, Endpoint, Manifest, Skill

manifest = Manifest(
    id="urn:asap:agent:my-echo",
    name="My Echo Agent",
    version="0.1.0",
    description="Echoes task input",
    capabilities=Capability(
        asap_version="0.1",
        skills=[Skill(id="echo", description="Echo back the input")],
        state_persistence=False,
    ),
    endpoints=Endpoint(asap="https://my-agent.example.com/asap"),
)`}</code>
                            </pre>
                        </div>

                        <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-6 space-y-4">
                            <h3 className="text-lg font-semibold text-white">Edge hardware &amp; inference (optional, v2.4+)</h3>
                            <p className="text-zinc-400 text-sm leading-relaxed">
                                Edge and physical agents may advertise structured hosting and inference under{' '}
                                <code className="text-indigo-400 bg-indigo-500/10 px-1 rounded font-mono text-xs">
                                    capabilities.hardware
                                </code>{' '}
                                and{' '}
                                <code className="text-indigo-400 bg-indigo-500/10 px-1 rounded font-mono text-xs">
                                    capabilities.inference
                                </code>
                                . All sub-fields are optional; omit the objects entirely if not applicable. The Lite
                                Registry mirrors these into{' '}
                                <code className="text-indigo-400 bg-indigo-500/10 px-1 rounded font-mono text-xs">
                                    hardware_class
                                </code>
                                ,{' '}
                                <code className="text-indigo-400 bg-indigo-500/10 px-1 rounded font-mono text-xs">
                                    inference_modes
                                </code>
                                , and{' '}
                                <code className="text-indigo-400 bg-indigo-500/10 px-1 rounded font-mono text-xs">
                                    hardware_io
                                </code>{' '}
                                when you register — you do not duplicate them in the IssueOps form when a manifest URL is
                                provided.
                            </p>
                            <p className="text-zinc-500 text-xs leading-relaxed">
                                Canonical JSON Schema:{' '}
                                <a
                                    href="https://github.com/asap-protocol/asap-protocol/blob/main/schemas/entities/manifest.schema.json"
                                    className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                >
                                    manifest.schema.json
                                </a>
                                . Example snippet:{' '}
                                <a
                                    href="https://github.com/asap-protocol/asap-protocol/blob/main/schemas/examples/shellclaw-jetson-capabilities.json"
                                    className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                >
                                    shellclaw-jetson-capabilities.json
                                </a>
                                . Closed enums and migration from free-form{' '}
                                <code className="text-indigo-400 bg-indigo-500/10 px-1 rounded font-mono text-xs">
                                    tags
                                </code>{' '}
                                (e.g. <code className="font-mono text-zinc-400">cuda</code>,{' '}
                                <code className="font-mono text-zinc-400">jetson</code>):{' '}
                                <a
                                    href="https://github.com/asap-protocol/asap-protocol/blob/main/docs/transport.md#hardware-and-inference-capabilities-v24"
                                    className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                >
                                    Transport docs — hardware &amp; inference
                                </a>
                                .
                            </p>
                            <p className="text-zinc-500 text-xs leading-relaxed">
                                Registry <code className="font-mono text-zinc-400">tags</code> remain a valid supplement
                                for human-readable discovery (frameworks, themes, trust labels added by CI). Prefer
                                structured fields for machine filtering (marketplace sidebar,{' '}
                                <code className="font-mono text-zinc-400">find_by_hardware_class</code>, etc.).
                            </p>
                            <div className="rounded-lg overflow-hidden border border-zinc-800 bg-zinc-950">
                                <pre className="p-4 text-xs font-mono text-zinc-300 overflow-x-auto leading-relaxed">
                                    <code>{`capabilities=Capability(
    asap_version="2.1.0",
    skills=[Skill(id="gpio_control", description="GPIO pin control")],
    state_persistence=True,
    streaming=True,
    hardware=HardwareCapability(
        class_="edge_accelerator",
        model="jetson_orin_nano_super_8gb",
        io=["gpio", "i2c"],
    ),
    inference=InferenceCapability(
        modes=["cloud", "local_cuda"],
        local_models=[
            LocalModelInfo(
                id="Phi-3-mini-4k-instruct-Q4_K_M",
                quantization="Q4_K_M",
            ),
        ],
    ),
)`}</code>
                                </pre>
                            </div>
                        </div>
                    </div>

                    <div className="space-y-6">
                        <div className="flex items-center gap-4">
                            <div className="flex items-center justify-center w-8 h-8 rounded-full bg-indigo-500/10 text-indigo-400 font-bold border border-indigo-500/20">
                                2
                            </div>
                            <h2 className="text-2xl font-bold text-white">Implement the ASAP Endpoint</h2>
                        </div>
                        <p className="text-zinc-400 leading-relaxed">
                            Your server needs to process the JSON-RPC 2.0 envelopes sent to your endpoint. The server must have a registered handler for standard payload types.
                        </p>

                        <div className="rounded-xl overflow-hidden border border-zinc-800 bg-zinc-900">
                            <div className="flex items-center justify-between px-4 py-2 border-b border-zinc-800 bg-zinc-950">
                                <span className="text-xs font-mono text-zinc-400">Server Handler Setup</span>
                            </div>
                            <pre className="p-6 text-sm font-mono text-zinc-300 overflow-x-auto leading-relaxed">
                                <code>{`from asap.transport.handlers import HandlerRegistry, create_echo_handler
from asap.transport.server import create_app

registry = HandlerRegistry()
# Register handlers for task capabilities
registry.register("task.request", create_echo_handler())

app = create_app(manifest, registry)`}</code>
                            </pre>
                        </div>
                    </div>

                    <div className="space-y-6 pt-8 border-t border-zinc-900">
                        <div className="flex items-center gap-4 mb-8">
                            <div className="flex items-center justify-center w-8 h-8 rounded-full bg-indigo-500/10 text-indigo-400 font-bold border border-indigo-500/20">
                                3
                            </div>
                            <h2 className="text-2xl font-bold text-white">Publish via IssueOps</h2>
                        </div>

                        <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-6 space-y-3">
                            <h3 className="text-lg font-semibold text-white">Built with (framework)</h3>
                            <p className="text-zinc-400 text-sm leading-relaxed">
                                Optional on registration. Use the same values in the{' '}
                                <a
                                    href="https://github.com/asap-protocol/asap-protocol/blob/main/.github/ISSUE_TEMPLATE/register_agent.yml"
                                    className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                >
                                    GitHub issue template
                                </a>{' '}
                                and the web dashboard:
                            </p>
                            <p className="text-sm font-mono text-zinc-300">
                                CrewAI · OpenClaw · ShellClaw · LangChain · AutoGen · Other
                            </p>
                            <p className="text-zinc-500 text-xs leading-relaxed">
                                C-native or static-manifest agents (GitHub Pages only, no live ASAP endpoint in v1.0)
                                may set{' '}
                                <code className="text-indigo-400 bg-indigo-500/10 px-1 rounded">online_check: false</code>
                                . See{' '}
                                <a
                                    href="https://github.com/asap-protocol/asap-protocol/blob/main/docs/guides/shellclaw-registry.md"
                                    className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                >
                                    ShellClaw static registry guide
                                </a>
                                .
                            </p>
                        </div>

                        <div className="grid md:grid-cols-2 gap-6">
                            <div className="p-6 rounded-xl border border-indigo-500/30 bg-indigo-500/5 relative group hover:bg-indigo-500/10 transition-colors">
                                <ShieldCheck className="w-6 h-6 text-indigo-400 mb-4" />
                                <h3 className="text-lg font-bold text-white mb-2">Web Dashboard (Recommended)</h3>
                                <p className="text-zinc-400 text-sm leading-relaxed mb-6">
                                    For v2.0 users, use our Web Dashboard to generate your IssueOps request in an automated way right from the web interface.
                                </p>
                                <Button asChild className="w-full bg-indigo-600 hover:bg-indigo-700 text-white border-0">
                                    <Link href="/dashboard/register">
                                        Go to Web Dashboard <ArrowRight className="ml-2 w-4 h-4" />
                                    </Link>
                                </Button>
                            </div>

                            <div className="p-6 rounded-xl border border-zinc-800 bg-zinc-900/40 relative group hover:bg-zinc-900/60 transition-colors">
                                <GitPullRequest className="w-6 h-6 text-zinc-400 mb-4" />
                                <h3 className="text-lg font-bold text-white mb-2">Manual IssueOps</h3>
                                <p className="text-zinc-400 text-sm leading-relaxed mb-6">
                                    Alternatively, you can open a GitHub Issue manually. Our CI pipeline will parse the template, validate the agent manifest, and merge it into the Lite Registry.
                                </p>
                                <Button asChild variant="secondary" className="w-full bg-zinc-800 hover:bg-zinc-700 text-white">
                                    <a href="https://github.com/asap-protocol/asap-protocol/issues/new/choose" target="_blank" rel="noopener noreferrer">
                                        Open Registration Issue <ArrowRight className="ml-2 w-4 h-4" />
                                    </a>
                                </Button>
                            </div>
                        </div>
                    </div>

                </div>
            </section>
        </div>
    );
}
