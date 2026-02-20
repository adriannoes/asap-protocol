import { Search, ShieldCheck, Cpu } from 'lucide-react';

const steps = [
  {
    title: 'Discover',
    description:
      'Browse the Lite Registry for agents matching your exact requirements, capabilities, and SLA needs.',
    icon: Search,
  },
  {
    title: 'Verify',
    description:
      "Check the agent's operations badge, trust scores, and historical performance metrics before integration.",
    icon: ShieldCheck,
  },
  {
    title: 'Integrate',
    description:
      'Connect via the ASAP Protocol over secure WebSockets. Standardized messages mean your code works with any agent.',
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
            Three simple steps to build robust multi-agent swarms.
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
                  key={index}
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
      </div>
    </section>
  );
}
