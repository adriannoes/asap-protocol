'use client';

import { Terminal } from 'lucide-react';
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
    <div
      className="mx-auto w-full max-w-[500px] lg:max-w-none animate-in fade-in zoom-in-95 duration-1000 delay-200 ease-out"
    >
      <div className="overflow-hidden rounded-xl border border-zinc-800 bg-zinc-950/50 border-white/10 backdrop-blur-xl">
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
  );
}
