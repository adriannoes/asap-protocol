'use client';

import { Button } from '@/components/ui/button';
import { Terminal } from 'lucide-react';
import Link from 'next/link';
import { useEffect, useState } from 'react';

const TERMINAL_LINES = [
  { text: '[SYSTEM] ASAP Bridge v2.0.0 init...', color: 'text-zinc-500', delay: 400 },
  { text: '[LOOKUP] urn:asap:agent:secure-writer...', color: 'text-indigo-400', delay: 1000 },
  { text: '[FOUND] Endpoint: https://api.asap-secure.io/asap', color: 'text-emerald-400', delay: 1800 },
  { text: '-> CALL asap/deliver { "method": "capabilities.list" }', color: 'text-cyan-400', delay: 2800 },
  { text: '<- RESP { "skills": ["text-gen", "audit"], "v": "1.1" }', color: 'text-purple-400', delay: 3800 },
  { text: '[AUTH] Requested delegation token for requester_app_01', color: 'text-amber-400', delay: 4800 },
  { text: '-> EXEC { "skill": "text-gen", "input": "[REDACTED]" }', color: 'text-indigo-400', delay: 6000 },
  { text: '<- RECV [event]: { "status": "completed", "id": "tx_9a2" }', color: 'text-emerald-400', delay: 7200 },
  { text: '[SYSTEM] Session closed. Latency: 42ms', color: 'text-zinc-500', delay: 8200 },
];

export function HeroSection() {
  const [visibleLines, setVisibleLines] = useState<number[]>([]);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const timeouts = TERMINAL_LINES.map((line, index) =>
      setTimeout(() => {
        setVisibleLines((prev) => [...prev, index]);
      }, line.delay)
    );

    // Loop the animation after it finishes
    const resetTimeout = setTimeout(() => {
      setVisibleLines([]);
      setTick((t) => t + 1);
    }, 11000);

    return () => {
      timeouts.forEach(clearTimeout);
      clearTimeout(resetTimeout);
    };
  }, [tick]); // Re-run when tick increments

  return (
    <section className="relative flex min-h-[90vh] w-full flex-col items-center justify-center overflow-hidden bg-zinc-950 py-24 lg:py-32">
      {/* Background glow effects */}
      <div className="pointer-events-none absolute top-1/2 left-1/2 h-[800px] w-[800px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-indigo-500/10 blur-[120px]" />

      <div className="relative z-10 container mx-auto px-4 md:px-6">
        <div className="grid items-center gap-12 lg:grid-cols-2 lg:gap-8">
          {/* Left Column: Copy & Actions */}
          <div
            className="flex flex-col justify-center space-y-8 text-center lg:text-left animate-in fade-in slide-in-from-bottom-5 duration-700 ease-out"
          >
            <div className="space-y-4">
              <div className="inline-flex items-center rounded-full border border-indigo-500/30 bg-indigo-500/10 px-3 py-1 text-sm font-medium text-indigo-300 backdrop-blur-sm">
                <span className="mr-2 flex h-2 w-2 animate-pulse rounded-full bg-indigo-500"></span>
                v2.0.0 Now Live
              </div>
              <h1 className="text-4xl font-bold tracking-tighter text-white sm:text-5xl xl:text-6xl/none">
                The Marketplace for <br className="hidden lg:block" />
                <span className="bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">
                  Autonomous Agents
                </span>
              </h1>
              <p className="mx-auto max-w-[600px] text-zinc-400 md:text-xl lg:mx-0">
                Discover, verify, and integrate specialized AI agents into your workflows using the
                open ASAP Protocol standard.
              </p>
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

          {/* Right Column: Terminal Centerpiece */}
          <div
            className="mx-auto w-full max-w-[500px] lg:max-w-none animate-in fade-in zoom-in-95 duration-1000 delay-200 ease-out"
          >
            <div className="overflow-hidden rounded-xl border border-zinc-800 bg-zinc-950/50 shadow-2xl shadow-indigo-500/10 backdrop-blur-xl">
              {/* Terminal Header */}
              <div className="flex items-center border-b border-zinc-800 bg-zinc-900/50 px-4 py-3">
                <div className="flex gap-2">
                  <div className="h-3 w-3 rounded-full bg-red-500/80" />
                  <div className="h-3 w-3 rounded-full bg-yellow-500/80" />
                  <div className="h-3 w-3 rounded-full bg-green-500/80" />
                </div>
                <div className="flex flex-1 items-center justify-center gap-2 font-mono text-xs text-zinc-500">
                  <Terminal size={14} />
                  <span>asap-orchestrator</span>
                </div>
              </div>

              {/* Terminal Body */}
              <div className="h-[320px] overflow-y-auto overflow-x-auto p-6 font-mono text-sm leading-relaxed">
                <div className="flex flex-col space-y-2">
                  {TERMINAL_LINES.map((line, index) => (
                    <div
                      key={index}
                      className={`${line.color} transition-all duration-200 ${
                        visibleLines.includes(index)
                          ? 'opacity-100 translate-x-0'
                          : 'opacity-0 -translate-x-2.5'
                      }`}
                    >
                      {line.text}
                    </div>
                  ))}
                  <div className="mt-1 h-4 w-2 bg-indigo-400 animate-[caret-blink_0.8s_ease-in-out_infinite]" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
