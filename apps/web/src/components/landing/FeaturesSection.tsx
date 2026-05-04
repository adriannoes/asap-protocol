import Link from 'next/link';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Database, ShieldCheck, Zap, Activity, ArrowRight, Fingerprint, KeySquare, Radio, FileCode, Braces, CloudUpload } from 'lucide-react';

const features = [
  {
    title: 'OpenAPI Adapter',
    slug: 'openapi-adapter',
    description:
      'Generate ASAP capabilities from an OpenAPI 3.x document so existing HTTP APIs become agent-callable with minimal glue code.',
    icon: FileCode,
    className: 'md:col-span-2',
  },
  {
    title: 'TypeScript SDK',
    slug: 'typescript-sdk',
    description:
      'Official `@asap-protocol/client` on npm — discovery, envelopes, streaming, plus optional Vercel AI, OpenAI, and Anthropic adapters.',
    icon: Braces,
    className: 'md:col-span-1',
  },
  {
    title: 'Auto-Registration',
    slug: 'auto-registration',
    description:
      'POST /registry/agents with Compliance Harness gating — shrink the time from “working agent” to “listed in the Lite Registry” without manual PR steps.',
    icon: CloudUpload,
    className: 'md:col-span-1',
  },
  {
    title: 'Lite Registry',
    slug: 'lite-registry',
    description:
      'Built for speed and resilience. Pull agent manifests directly from a statically served JSON registry with zero database overhead.',
    icon: Database,
    className: 'md:col-span-2',
  },
  {
    title: 'Verified Trust',
    slug: 'verified-trust',
    description:
      'Manual operations-based verification processes to ensure quality and safety across the ecosystem.',
    icon: ShieldCheck,
    className: 'md:col-span-1',
  },
  {
    title: '1-Click Integration',
    slug: '1-click-integration',
    description:
      'Launch sub-agents through a standard protocol that orchestrates connections over WebSockets natively.',
    icon: Zap,
    className: 'md:col-span-1',
  },
  {
    title: 'Full Observability',
    slug: 'full-observability',
    description:
      'Real-time stream of agent events, state snapshots, and task updates standardized across the network.',
    icon: Activity,
    className: 'md:col-span-2',
  },
  {
    title: 'Per-Agent Identity',
    slug: 'per-agent-identity',
    description:
      'Every runtime agent gets its own Ed25519 keypair under a persistent Host. Audit, scope, and revoke individual sessions without touching the rest of your fleet.',
    icon: Fingerprint,
    className: 'md:col-span-1',
  },
  {
    title: 'Scoped Capabilities',
    slug: 'scoped-capabilities',
    description:
      'Fine-grained capabilities with constraint operators — transfer up to $1,000, only in USD, to one destination. Precise grants replace coarse OAuth scopes.',
    icon: KeySquare,
    className: 'md:col-span-1',
  },
  {
    title: 'Streaming Responses',
    slug: 'streaming-responses',
    description:
      'TaskStream chunks over Server-Sent Events. Show partial results and progress in real time instead of blocking until completion.',
    icon: Radio,
    className: 'md:col-span-1',
  },
];

export function FeaturesSection() {
  return (
    <section className="w-full bg-zinc-950 py-24">
      <div className="container mx-auto px-4 md:px-6">
        <div className="mb-12 flex flex-col gap-4 text-center">
          <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
            Protocol Features
          </h2>
          <p className="mx-auto max-w-[600px] text-zinc-400">
            Everything you need to orchestrate complex multi-agent systems reliably — identity, capabilities, streaming, and v2.3 adoption tools (OpenAPI, TypeScript SDK, auto-registration).
          </p>
        </div>

        <div className="mx-auto grid max-w-5xl grid-cols-1 gap-6 md:grid-cols-3">
          {features.map((feature, i) => {
            const Icon = feature.icon;
            return (
              <Link key={i} href={`/features/${feature.slug}`} className={`group ${feature.className}`}>
                <Card
                  className={`relative h-full overflow-hidden border-zinc-800 bg-zinc-950 transition-all duration-300 hover:border-indigo-500/50`}
                >
                  <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 via-transparent to-transparent opacity-0 transition-opacity delay-75 duration-500 group-hover:opacity-100" />
                  <CardHeader>
                    <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg border border-zinc-800 bg-zinc-900 transition-colors group-hover:border-indigo-500/50 group-hover:bg-indigo-950/30">
                      <Icon className="h-6 w-6 text-indigo-400" />
                    </div>
                    <CardTitle className="text-xl text-white">{feature.title}</CardTitle>
                  </CardHeader>
                  <CardContent className="flex flex-col gap-4">
                    <CardDescription className="text-base text-zinc-400">
                      {feature.description}
                    </CardDescription>
                    <div className="mt-auto flex items-center pt-4 text-sm font-medium text-indigo-400 opacity-0 transition-opacity duration-300 group-hover:opacity-100">
                      Explore feature <ArrowRight className="ml-1 h-4 w-4" />
                    </div>
                  </CardContent>
                </Card>
              </Link>
            );
          })}
        </div>
      </div>
    </section>
  );
}
