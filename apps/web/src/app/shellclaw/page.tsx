import { Metadata } from 'next';
import Link from 'next/link';
import {
    ArrowRight,
    Camera,
    CircuitBoard,
    Cpu,
    Github,
    HardDrive,
    Layers,
    MemoryStick,
    Store,
    Zap,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { BackgroundPaths } from '@/components/ui/background-paths';

const SHELLCLAW_GITHUB = 'https://github.com/adriannoes/shellclaw';

export const metadata: Metadata = {
    title: 'ShellClaw | Physical Agent · Edge AI | ASAP Protocol',
    description:
        'ShellClaw is the first physical AI agent in the ASAP marketplace — a C-native aarch64 binary that scales from Raspberry Pi Zero 2 W to NVIDIA Jetson Orin Nano Super.',
    openGraph: {
        title: 'ShellClaw | Physical Agent · Edge AI | ASAP Protocol',
        description:
            'ShellClaw is the first physical AI agent in the ASAP marketplace — a C-native aarch64 binary that scales from Raspberry Pi Zero 2 W to NVIDIA Jetson Orin Nano Super.',
        type: 'website',
    },
};

const METRICS = [
    {
        icon: HardDrive,
        label: 'Binary size',
        value: '< 500 KB',
        detail: 'Base image; < 600 KB with hardware backends',
    },
    {
        icon: MemoryStick,
        label: 'Agent RAM',
        value: '< 5 MB',
        detail: 'Idle footprint on both target boards',
    },
    {
        icon: CircuitBoard,
        label: 'Hardware I/O',
        value: 'GPIO · I2C · Camera',
        detail: 'Single abstraction with per-board backends',
    },
    {
        icon: Store,
        label: 'Agent network',
        value: 'ASAP marketplace',
        detail: 'First non-Python edge-AI ASAP agent',
    },
] as const;

const PERSONAS = [
    {
        title: 'Jetson Orin Nano Super',
        persona: 'Edge-AI maker / researcher',
        specs: [
            '8 GB RAM, 67 TOPS',
            'Llama-3.1-8B Q4 @ 14–18 tok/s via CUDA',
            'Phi-3-mini Q4 @ 25–35 tok/s',
            'GPIO, I2C, CSI camera, NVMe boot',
        ],
    },
    {
        title: 'Raspberry Pi Zero 2 W',
        persona: 'Hobbyist / IoT tinkerer',
        specs: [
            '< 5 MB RAM, < 500 KB binary',
            'Smallest viable Linux SBC target',
            'GPIO, I2C, CSI camera',
            'Cloud LLM primary; TinyLlama emergency fallback',
        ],
    },
] as const;

const ROADMAP = [
    { version: 'v0.1', label: 'Foundation', status: 'done', focus: 'Core agent loop, CLI, Telegram, tools, SQLite memory' },
    { version: 'v0.2', label: 'Gateway', status: 'done', focus: 'HTTP server, Web UI, WebSocket, cron, ASAP manifest' },
    { version: 'v0.3', label: 'Protocol', status: 'done', focus: 'ASAP client/server, registry, sandbox, rate limits' },
    { version: 'v0.4', label: 'Autonomy', status: 'done', focus: 'Local inference, Discord, systemd, OTA updates' },
    { version: 'v1.0', label: 'Jetson release', status: 'in_progress', focus: 'CUDA LLM, GPIO/I2C/camera, Ed25519 signing, marketplace registration' },
    { version: 'v1.1', label: 'RPi portability', status: 'planned', focus: 'Same binary validated on Pi Zero 2 W, install script, benchmarks' },
] as const;

export default function ShellClawPage() {
    return (
        <div className="flex min-h-screen flex-col bg-zinc-950 font-sans text-zinc-300 selection:bg-indigo-500/30">
            <div className="pointer-events-none fixed inset-0 z-0 flex justify-center opacity-[0.03]">
                <div className="flex h-full w-full max-w-7xl justify-between border-x border-zinc-500">
                    <div className="h-full w-px bg-zinc-500" />
                    <div className="hidden h-full w-px bg-zinc-500 md:block" />
                    <div className="hidden h-full w-px bg-zinc-500 lg:block" />
                </div>
            </div>

            <section className="relative z-10 overflow-hidden border-b border-zinc-900 py-24 lg:py-32">
                <BackgroundPaths pathCount={4} />
                <div className="container relative mx-auto px-4 text-center md:px-6">
                    <div className="mb-8 inline-flex items-center rounded-md border border-zinc-800 bg-zinc-900/50 px-3 py-1 font-mono text-[11px] uppercase tracking-wider text-zinc-400">
                        <Cpu className="mr-2 h-3 w-3 text-indigo-400" />
                        Physical Agent · Edge AI
                    </div>
                    <h1 className="mb-6 text-4xl font-bold tracking-tight text-white md:text-5xl lg:text-7xl">
                        ShellClaw
                    </h1>
                    <p className="mx-auto mb-10 max-w-[720px] text-zinc-400 md:text-xl">
                        The first physical AI agent in the ASAP marketplace — a C-native{' '}
                        <code className="rounded bg-indigo-500/10 px-1 py-0.5 text-sm text-indigo-400">aarch64</code>{' '}
                        binary that scales from Raspberry Pi to NVIDIA Jetson with runtime board detection.
                    </p>
                    <div className="flex flex-col items-center justify-center gap-4 sm:flex-row">
                        <Button asChild size="lg" className="bg-white text-zinc-950 hover:bg-zinc-200">
                            <a href={SHELLCLAW_GITHUB} target="_blank" rel="noopener noreferrer">
                                <Github className="mr-2 h-4 w-4" />
                                View on GitHub
                            </a>
                        </Button>
                        <Button
                            asChild
                            size="lg"
                            variant="outline"
                            className="border-zinc-800 text-zinc-300 hover:bg-zinc-900 hover:text-white"
                        >
                            <Link href="/docs/register">
                                Registry guide <ArrowRight className="ml-2 h-4 w-4" />
                            </Link>
                        </Button>
                    </div>
                </div>
            </section>

            <section className="relative z-10 border-b border-zinc-900 bg-zinc-950/50 py-24">
                <div className="container mx-auto px-4 md:px-6">
                    <div className="mb-16 max-w-3xl">
                        <h2 className="mb-4 font-mono text-2xl font-bold tracking-tight text-white">
                            <span className="mr-2 text-indigo-500">01.</span> Built for the edge
                        </h2>
                        <p className="text-zinc-400">
                            ShellClaw is not another chat wrapper — it is a hardware-native agent that interacts with GPIO,
                            I2C sensors, and cameras while collaborating with cloud agents through ASAP Protocol.
                        </p>
                    </div>

                    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
                        {METRICS.map((metric) => {
                            const Icon = metric.icon;
                            return (
                                <div
                                    key={metric.label}
                                    className="group flex h-full flex-col rounded-lg border border-zinc-800 bg-zinc-900/30 p-6 transition-colors hover:border-zinc-700"
                                >
                                    <Icon className="mb-4 h-5 w-5 text-zinc-500 transition-colors group-hover:text-indigo-400" />
                                    <p className="mb-1 font-mono text-[11px] uppercase tracking-wider text-zinc-500">
                                        {metric.label}
                                    </p>
                                    <p className="mb-2 text-xl font-bold text-white">{metric.value}</p>
                                    <p className="text-sm leading-relaxed text-zinc-400">{metric.detail}</p>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </section>

            <section className="relative z-10 border-b border-zinc-900 bg-zinc-950 py-24">
                <div className="container mx-auto px-4 md:px-6">
                    <div className="mb-16 max-w-3xl">
                        <h2 className="mb-4 font-mono text-2xl font-bold tracking-tight text-white">
                            <span className="mr-2 text-indigo-500">02.</span> Two personas, one binary
                        </h2>
                        <p className="text-zinc-400">
                            Runtime board detection reads{' '}
                            <code className="rounded bg-indigo-500/10 px-1 py-0.5 text-sm text-indigo-400">
                                /proc/device-tree/compatible
                            </code>{' '}
                            at startup and selects the right hardware backends — same source tree, same binary.
                        </p>
                    </div>

                    <div className="grid gap-6 lg:grid-cols-2">
                        {PERSONAS.map((board) => (
                            <div
                                key={board.title}
                                className="flex h-full flex-col rounded-lg border border-zinc-800 bg-zinc-900/30 p-8 transition-colors hover:border-zinc-700"
                            >
                                <div className="mb-6">
                                    <h3 className="text-lg font-bold tracking-tight text-white">{board.title}</h3>
                                    <p className="mt-1 text-sm text-indigo-400">{board.persona}</p>
                                </div>
                                <ul className="space-y-3">
                                    {board.specs.map((spec) => (
                                        <li key={spec} className="flex items-start gap-2 text-sm text-zinc-400">
                                            <Zap className="mt-0.5 h-3.5 w-3.5 shrink-0 text-indigo-400" />
                                            <span>{spec}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            <section className="relative z-10 border-b border-zinc-900 bg-zinc-950/50 py-24">
                <div className="container mx-auto px-4 md:px-6">
                    <div className="grid items-center gap-16 lg:grid-cols-2 lg:gap-12">
                        <div className="space-y-6">
                            <h2 className="font-mono text-2xl font-bold tracking-tight text-white">
                                <span className="mr-2 text-indigo-500">03.</span> ASAP integration
                            </h2>
                            <p className="leading-relaxed text-zinc-400">
                                ShellClaw is the first non-Python ASAP agent and the first edge-AI agent in the ecosystem.
                                It registers on the marketplace, exposes an ASAP manifest, and invokes peer agents through
                                the standardized protocol.
                            </p>
                            <p className="leading-relaxed text-zinc-400">
                                Discover edge-capable agents in the registry or follow the onboarding guide to publish your
                                own hardware-backed manifest.
                            </p>
                            <div className="flex flex-col gap-3 sm:flex-row">
                                <Button asChild variant="outline" className="border-zinc-800 text-zinc-300 hover:bg-zinc-900 hover:text-white">
                                    <Link href="/browse">
                                        <Layers className="mr-2 h-4 w-4" />
                                        Browse marketplace
                                    </Link>
                                </Button>
                                <Button asChild variant="outline" className="border-zinc-800 text-zinc-300 hover:bg-zinc-900 hover:text-white">
                                    <Link href="/docs/register">
                                        Register your agent
                                        <ArrowRight className="ml-2 h-4 w-4" />
                                    </Link>
                                </Button>
                            </div>
                        </div>

                        <div className="overflow-hidden rounded-lg border border-zinc-800 bg-zinc-900/50 font-mono text-sm leading-relaxed">
                            <div className="flex border-b border-zinc-800 bg-zinc-950 px-4 py-2 text-xs text-zinc-500">
                                <div className="flex-1">agent_loop.c</div>
                                <div className="hidden sm:block">Physical + protocol</div>
                            </div>
                            <div className="space-y-1 p-4 text-zinc-300">
                                <p>
                                    <span className="text-indigo-400">Channels</span>{' '}
                                    <span className="text-zinc-500">→ Telegram · Discord · WebChat</span>
                                </p>
                                <p>
                                    <span className="text-indigo-400">Agent loop</span>{' '}
                                    <span className="text-zinc-500">→ ReAct + local LLM (CUDA / CPU)</span>
                                </p>
                                <p>
                                    <span className="text-indigo-400">Tools</span>{' '}
                                    <span className="text-zinc-500">→ shell · search · file · asap_invoke</span>
                                </p>
                                <p className="flex items-center gap-2">
                                    <Camera className="h-3.5 w-3.5 text-indigo-400" />
                                    <span className="text-indigo-400">Hardware</span>{' '}
                                    <span className="text-zinc-500">→ GPIO · I2C · CSI/USB camera</span>
                                </p>
                                <p>
                                    <span className="text-indigo-400">ASAP</span>{' '}
                                    <span className="text-zinc-500">→ marketplace + peer agents</span>
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            <section className="relative z-10 border-b border-zinc-900 bg-zinc-950 py-24">
                <div className="container mx-auto px-4 md:px-6">
                    <div className="mb-16 max-w-3xl">
                        <h2 className="mb-4 font-mono text-2xl font-bold tracking-tight text-white">
                            <span className="mr-2 text-indigo-500">04.</span> Roadmap
                        </h2>
                        <p className="text-zinc-400">
                            Foundation through autonomy (v0.1–v0.4) is complete. Edge-AI hardware release on Jetson (v1.0)
                            and Raspberry Pi portability (v1.1) are next.
                        </p>
                    </div>

                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                        {ROADMAP.map((phase) => (
                            <div
                                key={phase.version}
                                className="flex h-full flex-col rounded-lg border border-zinc-800 bg-zinc-900/20 p-5 transition-colors hover:border-zinc-700"
                            >
                                <div className="mb-3 flex items-center justify-between gap-2">
                                    <span className="font-mono text-sm font-bold text-white">{phase.version}</span>
                                    <span
                                        className={
                                            phase.status === 'done'
                                                ? 'rounded border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-emerald-400'
                                                : phase.status === 'in_progress'
                                                  ? 'rounded border border-indigo-500/30 bg-indigo-500/10 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-indigo-400'
                                                  : 'rounded border border-zinc-700 bg-zinc-900 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-zinc-500'
                                        }
                                    >
                                        {phase.status === 'done'
                                            ? 'Done'
                                            : phase.status === 'in_progress'
                                              ? 'In progress'
                                              : 'Planned'}
                                    </span>
                                </div>
                                <h3 className="mb-2 text-sm font-bold uppercase tracking-wide text-zinc-300">
                                    {phase.label}
                                </h3>
                                <p className="text-sm leading-relaxed text-zinc-500">{phase.focus}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            <section className="relative z-10 bg-zinc-950 py-32 text-center">
                <div className="container mx-auto px-4">
                    <h2 className="mb-4 text-2xl font-bold tracking-tight text-white">
                        Run ShellClaw on real hardware
                    </h2>
                    <p className="mx-auto mb-8 max-w-xl text-zinc-400">
                        Clone the repo, build with{' '}
                        <code className="rounded bg-indigo-500/10 px-1 py-0.5 text-sm text-indigo-400">make shellclaw</code>,
                        and join the ASAP agent marketplace.
                    </p>
                    <div className="flex flex-col justify-center gap-4 sm:flex-row">
                        <Button asChild size="lg" className="bg-white text-zinc-950 hover:bg-zinc-200">
                            <a href={SHELLCLAW_GITHUB} target="_blank" rel="noopener noreferrer">
                                <Github className="mr-2 h-4 w-4" />
                                github.com/adriannoes/shellclaw
                            </a>
                        </Button>
                        <Button
                            asChild
                            size="lg"
                            variant="outline"
                            className="border-zinc-800 text-zinc-300 hover:bg-zinc-900 hover:text-white"
                        >
                            <Link href="/docs/register">
                                Publish to registry <ArrowRight className="ml-2 h-4 w-4" />
                            </Link>
                        </Button>
                    </div>
                </div>
            </section>
        </div>
    );
}
