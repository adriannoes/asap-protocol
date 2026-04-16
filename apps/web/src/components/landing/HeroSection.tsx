import { AnimatedText } from '@/components/ui/animated-text';
import { Button } from '@/components/ui/button';
import { BackgroundPaths } from '@/components/ui/background-paths';
import { HeroTerminal } from '@/components/landing/HeroTerminal';
import Link from 'next/link';

export function HeroSection() {
  return (
    <section className="relative flex min-h-[90vh] w-full flex-col items-center justify-center overflow-hidden bg-zinc-950 py-24 lg:py-32">
      <BackgroundPaths />
      <div className="pointer-events-none absolute top-1/2 left-1/2 h-[800px] w-[800px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-indigo-500/10 blur-[120px]" />

      <div className="relative z-10 container mx-auto px-4 md:px-6">
        <div className="grid items-center gap-12 lg:grid-cols-2 lg:gap-8">
          <div
            className="flex flex-col justify-center space-y-8 text-center lg:text-left animate-in fade-in slide-in-from-bottom-5 duration-700 ease-out"
          >
            <div className="space-y-4">
              <Link
                href="https://github.com/adriannoes/asap-protocol/blob/main/CHANGELOG.md"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="View ASAP Protocol v2.2.0 changelog on GitHub"
              >
                <div className="inline-flex items-center rounded-full border border-indigo-500/30 bg-indigo-500/10 px-3 py-1 text-sm font-medium text-indigo-300 backdrop-blur-sm transition-colors hover:border-indigo-500/60 hover:bg-indigo-500/15">
                  <span className="mr-2 flex h-2 w-2 animate-pulse rounded-full bg-indigo-500"></span>
                  v2.2.0 Now Live
                </div>
              </Link>
              <AnimatedText
                text="The Marketplace for Autonomous Agents"
                className="text-4xl font-bold tracking-tighter leading-tight sm:text-5xl xl:text-6xl/none bg-clip-text text-transparent bg-gradient-to-r from-white to-white/80"
              />
              <AnimatedText
                text="Discover, verify, and integrate specialized AI agents into your workflows using the open ASAP Protocol standard."
                as="p"
                delay={0.3}
                className="mx-auto max-w-[600px] text-zinc-400 md:text-xl lg:mx-0"
              />
            </div>

            <div className="flex flex-col justify-center gap-4 min-[400px]:flex-row lg:justify-start">
              <Button
                asChild
                size="lg"
                className="w-full bg-white text-black hover:bg-zinc-200 min-[400px]:w-auto"
              >
                <Link href="/browse">
                  Explore Agents
                </Link>
              </Button>
              <Button
                asChild
                size="lg"
                variant="outline"
                className="w-full border-zinc-800 text-zinc-300 hover:bg-zinc-900 hover:text-white min-[400px]:w-auto"
              >
                <Link href="/dashboard/register">
                  Register Agent
                </Link>
              </Button>
            </div>
          </div>

          <HeroTerminal />
        </div>
      </div>
    </section>
  );
}
