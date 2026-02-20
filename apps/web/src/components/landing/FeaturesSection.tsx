import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Database, ShieldCheck, Zap, Activity } from 'lucide-react';

const features = [
  {
    title: 'Lite Registry',
    description:
      'Built for speed and resilience. Pull agent manifests directly from a statically served JSON registry with zero database overhead.',
    icon: Database,
    className: 'md:col-span-2',
  },
  {
    title: 'Verified Trust',
    description:
      'Manual operations-based verification processes to ensure quality and safety across the ecosystem.',
    icon: ShieldCheck,
    className: 'md:col-span-1',
  },
  {
    title: '1-Click Integration',
    description:
      'Launch sub-agents through a standard protocol that orchestrates connections over WebSockets natively.',
    icon: Zap,
    className: 'md:col-span-1',
  },
  {
    title: 'Full Observability',
    description:
      'Real-time stream of agent events, state snapshots, and task updates standardized across the network.',
    icon: Activity,
    className: 'md:col-span-2',
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
            Everything you need to orchestrate complex multi-agent systems reliably.
          </p>
        </div>

        <div className="mx-auto grid max-w-5xl grid-cols-1 gap-6 md:grid-cols-3">
          {features.map((feature, i) => {
            const Icon = feature.icon;
            return (
              <Card
                key={i}
                className={`group relative overflow-hidden border-zinc-800 bg-zinc-950 transition-all duration-300 hover:border-indigo-500/50 ${feature.className}`}
              >
                {/* Hover gradient background effect */}
                <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 via-transparent to-transparent opacity-0 transition-opacity delay-75 duration-500 group-hover:opacity-100" />

                <CardHeader>
                  <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg border border-zinc-800 bg-zinc-900 transition-colors group-hover:border-indigo-500/50 group-hover:bg-indigo-950/30">
                    <Icon className="h-6 w-6 text-indigo-400" />
                  </div>
                  <CardTitle className="text-xl text-white">{feature.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription className="text-base text-zinc-400">
                    {feature.description}
                  </CardDescription>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>
    </section>
  );
}
