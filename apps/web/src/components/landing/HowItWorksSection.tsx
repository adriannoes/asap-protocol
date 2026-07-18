import Link from 'next/link';
import { Search, ShieldCheck, KeySquare, Cpu } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { HOW_IT_WORKS_CTA_IDS } from '@/lib/telemetry/homepage-cta-ids';
import { BUILD_FOR_AGENTS_GUIDE_URL, STARTERS_URL } from '@/lib/landing/dist-loop-links';
import { EXTERNAL_LINK_FOCUS_CLASS, OpensInNewTabHint } from '@/components/links/opens-in-new-tab';

const steps = [
  {
    title: 'Discover',
    description:
      'Find agent-ready capabilities via manifests and the Lite Registry — or start from OpenAPI and adapters in the Build for agents guide.',
    icon: Search,
  },
  {
    title: 'Verify',
    description:
      'Run compliance checks and review trust signals before you wire an agent into production workflows.',
    icon: ShieldCheck,
  },
  {
    title: 'Authorize',
    description:
      'Grant fine-grained capabilities with constraints — for example, "transfer up to $1,000 USD only". Each runtime agent gets its own Ed25519 identity, so you can revoke a single session without touching the rest of your fleet.',
    icon: KeySquare,
  },
  {
    title: 'Integrate',
    description:
      'Connect with official SDKs and thin starters (OpenAPI provider, TypeScript consumer, MCP Auth Bridge) so existing APIs become agent-ready interfaces.',
    icon: Cpu,
  },
];

export function HowItWorksSection() {
  return (
    <section className="w-full border-t border-zinc-900 bg-zinc-950/80 py-24">
      <div className="container mx-auto px-4 md:px-6">
        <div className="mb-16 flex flex-col gap-4 text-center">
          <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">How it works</h2>
          <p className="mx-auto max-w-[600px] text-zinc-400">
            Four steps from agent-ready APIs to scoped, compliant multi-agent workflows.
          </p>
        </div>

        <div className="relative mx-auto max-w-3xl">
          {/* Vertical connecting line */}
          <div className="absolute top-0 bottom-0 left-[39px] w-px bg-zinc-800 md:left-1/2 md:-translate-x-1/2" />

          <div className="space-y-12">
            {steps.map((step, index) => {
              const Icon = step.icon;
              const isEven = index % 2 === 0;

              return (
                <div
                  key={step.title}
                  className="relative flex flex-col items-center gap-8 md:flex-row md:gap-12"
                >
                  {/* Left Column (Desktop) */}
                  <div
                    className={`w-full pl-24 md:flex-1 md:pl-0 ${isEven ? 'md:text-right' : 'md:order-last md:text-left'}`}
                  >
                    <h3 className="mb-2 text-xl font-bold text-white">{step.title}</h3>
                    <p className="text-zinc-400">{step.description}</p>
                  </div>

                  {/* Center Node */}
                  <div className="absolute left-6 z-10 flex h-14 w-14 shrink-0 items-center justify-center rounded-full border-4 border-zinc-950 bg-indigo-500/20 text-indigo-400 ring-1 ring-zinc-800 backdrop-blur-md md:static md:left-auto md:order-none">
                    <Icon className="h-6 w-6" />
                  </div>

                  {/* Right Column (Desktop spacer or content) */}
                  <div
                    className={`hidden md:block md:flex-1 ${!isEven ? 'text-right' : 'text-left'}`}
                  >
                    {/* Empty space for alternating layout */}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="mt-16 flex flex-col items-center justify-center gap-4 min-[400px]:flex-row">
          <Button
            asChild
            size="lg"
            className="w-full bg-white text-black hover:bg-zinc-200 min-[400px]:w-auto"
          >
            <Link
              href={BUILD_FOR_AGENTS_GUIDE_URL}
              target="_blank"
              rel="noopener noreferrer"
              data-cta={HOW_IT_WORKS_CTA_IDS.buildForAgents}
              className={EXTERNAL_LINK_FOCUS_CLASS}
            >
              Build for agents
              <OpensInNewTabHint />
            </Link>
          </Button>
          <Button
            asChild
            size="lg"
            variant="outline"
            className="w-full border-zinc-800 text-zinc-300 hover:bg-zinc-900 hover:text-white min-[400px]:w-auto"
          >
            <Link
              href={STARTERS_URL}
              target="_blank"
              rel="noopener noreferrer"
              data-cta={HOW_IT_WORKS_CTA_IDS.viewStarters}
              className={EXTERNAL_LINK_FOCUS_CLASS}
            >
              View starters
              <OpensInNewTabHint />
            </Link>
          </Button>
        </div>
      </div>
    </section>
  );
}
