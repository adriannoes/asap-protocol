'use client';

import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Terminal } from 'lucide-react';
import Link from 'next/link';
import { useEffect, useState } from 'react';

const CODE_LINES = [
  'from asap import Agent\n\n',
  '# Connect to the marketplace\n',
  'agent = await Agent.connect()\n\n',
  '# Discover high-trust agents\n',
  'registry = await agent.get_registry()\n',
  "trusted = registry.filter(trust_score='>90')\n\n",
  '# Delegate task seamlessly\n',
  'response = await trusted[0].send_task(\n',
  "    'Analyze contract and extract terms'\n",
  ')\n',
  'print(response.result)\n',
];

export function HeroSection() {
  const [typedCode, setTypedCode] = useState('');
  const [lineIndex, setLineIndex] = useState(0);

  // Simple typing effect for the code block
  useEffect(() => {
    if (lineIndex < CODE_LINES.length) {
      const timeout = setTimeout(
        () => {
          setTypedCode((prev) => prev + CODE_LINES[lineIndex]);
          setLineIndex((prev) => prev + 1);
        },
        Math.random() * 400 + 200
      ); // Random delay between 200ms and 600ms per line
      return () => clearTimeout(timeout);
    }
  }, [lineIndex]);

  return (
    <section className="relative flex min-h-[90vh] w-full flex-col items-center justify-center overflow-hidden bg-zinc-950 py-24 lg:py-32">
      {/* Background glow effects */}
      <div className="pointer-events-none absolute top-1/2 left-1/2 h-[800px] w-[800px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-indigo-500/10 blur-[120px]" />

      <div className="relative z-10 container mx-auto px-4 md:px-6">
        <div className="grid items-center gap-12 lg:grid-cols-2 lg:gap-8">
          {/* Left Column: Copy & Actions */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
            className="flex flex-col justify-center space-y-8 text-center lg:text-left"
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
              <Link href="/browse">
                <Button
                  size="lg"
                  className="w-full bg-white text-black hover:bg-zinc-200 min-[400px]:w-auto"
                >
                  Explore Agents
                </Button>
              </Link>
              <Link href="/docs/register">
                <Button
                  size="lg"
                  variant="outline"
                  className="w-full border-zinc-800 text-zinc-300 hover:bg-zinc-900 hover:text-white min-[400px]:w-auto"
                >
                  Register Agent
                </Button>
              </Link>
            </div>
          </motion.div>

          {/* Right Column: Terminal Centerpiece */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 1, delay: 0.2, ease: 'easeOut' }}
            className="mx-auto w-full max-w-[500px] lg:max-w-none"
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
                  <span>integration.py</span>
                </div>
              </div>

              {/* Terminal Body */}
              <div className="overflow-x-auto p-6 font-mono text-sm leading-relaxed">
                <pre className="text-zinc-300">
                  <code>
                    {/* Basic syntax coloring simulation using spans inside the typed string would be complex without a highlighter, so we keep it simple or apply basic regex replacements if needed. For now, monochromatic with a colored cursor */}
                    {typedCode}
                    <motion.span
                      animate={{ opacity: [1, 0] }}
                      transition={{ repeat: Infinity, duration: 0.8 }}
                      className="ml-1 inline-block h-4 w-2 translate-y-1 bg-indigo-400"
                    />
                  </code>
                </pre>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
