'use client';

import { Terminal } from 'lucide-react';
import { useEffect, useState } from 'react';

/**
 * Dist Loop / Build for agents framing — path names and starter ids only.
 * Do not invent fake JSON-RPC / SSE payloads here.
 */
const TERMINAL_LINES = [
  {
    text: '[TRAIN] ASAP Distribution Loop — Build for agents',
    color: 'text-zinc-400',
    delay: 400,
  },
  {
    text: '[GUIDE] docs/guides/build-for-agents.md',
    color: 'text-indigo-300',
    delay: 1000,
  },
  {
    text: '[STARTERS] openapi-provider · typescript-consumer · mcp-auth-bridge',
    color: 'text-cyan-300',
    delay: 1800,
  },
  {
    text: '[FOUNDATION] discoverable capabilities · scoped identity · compliance',
    color: 'text-purple-300',
    delay: 2800,
  },
  {
    text: '[ADAPTER] OpenAPI → agent-ready interface (examples/starters/openapi-provider)',
    color: 'text-amber-300',
    delay: 3800,
  },
  {
    text: '[SDK] @asap-protocol/client · examples/starters/typescript-consumer',
    color: 'text-indigo-300',
    delay: 4800,
  },
  {
    text: '[MCP] Auth Bridge starter · examples/starters/mcp-auth-bridge',
    color: 'text-emerald-300',
    delay: 6000,
  },
  {
    text: '[MARKETPLACE] browse / register remain secondary proof',
    color: 'text-zinc-500',
    delay: 7200,
  },
  {
    text: '[READY] primary CTAs → guide + starters',
    color: 'text-emerald-300',
    delay: 8200,
  },
];

const LOOP_RESET_DELAY = 11000;

export function HeroTerminal() {
  const [visibleLines, setVisibleLines] = useState<number[]>([]);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const timeouts = TERMINAL_LINES.map((line, index) =>
      setTimeout(() => {
        setVisibleLines((prev) => [...prev, index]);
      }, line.delay)
    );

    const resetTimeout = setTimeout(() => {
      setVisibleLines([]);
      setTick((t) => t + 1);
    }, LOOP_RESET_DELAY);

    return () => {
      timeouts.forEach(clearTimeout);
      clearTimeout(resetTimeout);
    };
  }, [tick]);

  return (
    <div className="animate-in fade-in zoom-in-95 mx-auto w-full max-w-[500px] delay-200 duration-1000 ease-out lg:max-w-none">
      <div className="overflow-hidden rounded-xl border border-white/10 border-zinc-800 bg-zinc-950/50 backdrop-blur-xl">
        <div className="flex items-center border-b border-zinc-800 bg-zinc-900/50 px-4 py-3">
          <div className="flex gap-2">
            <div className="h-3 w-3 rounded-full bg-red-500/80" />
            <div className="h-3 w-3 rounded-full bg-yellow-500/80" />
            <div className="h-3 w-3 rounded-full bg-green-500/80" />
          </div>
          <div className="flex flex-1 items-center justify-center gap-2 font-mono text-xs text-zinc-500">
            <Terminal size={14} />
            <span>asap-build-for-agents</span>
          </div>
        </div>

        <div className="h-[320px] overflow-x-auto overflow-y-auto p-6 font-mono text-sm leading-relaxed">
          <div className="flex flex-col space-y-2">
            {TERMINAL_LINES.map((line, index) => (
              <div
                key={index}
                className={`${line.color} transition-all duration-200 ${
                  visibleLines.includes(index)
                    ? 'translate-x-0 opacity-100'
                    : '-translate-x-2.5 opacity-0'
                }`}
              >
                {line.text}
              </div>
            ))}
            <div className="mt-1 h-4 w-2 animate-[caret-blink_0.8s_ease-in-out_infinite] bg-indigo-400" />
          </div>
        </div>
      </div>
    </div>
  );
}
