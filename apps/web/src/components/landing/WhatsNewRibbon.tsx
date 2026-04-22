import Link from 'next/link';
import {
  Fingerprint,
  KeySquare,
  Radio,
  GitBranch,
  Layers,
  ShieldCheck,
  Sparkles,
  ArrowUpRight,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

type Pill = {
  label: string;
  href: string;
  icon: LucideIcon;
  external?: boolean;
};

const CHANGELOG_URL =
  'https://github.com/adriannoes/asap-protocol/blob/main/CHANGELOG.md#221---2026-04-21';

const PILLS: Pill[] = [
  { label: 'Identity', href: '/features/per-agent-identity', icon: Fingerprint },
  { label: 'Capabilities', href: '/features/scoped-capabilities', icon: KeySquare },
  { label: 'Streaming', href: '/features/streaming-responses', icon: Radio },
  { label: 'Versioning', href: CHANGELOG_URL, icon: GitBranch, external: true },
  { label: 'Batch', href: CHANGELOG_URL, icon: Layers, external: true },
  { label: 'WebAuthn', href: CHANGELOG_URL, icon: ShieldCheck, external: true },
];

export function WhatsNewRibbon() {
  return (
    <aside
      aria-label="What's new in ASAP Protocol v2.2.1"
      className="w-full border-y border-zinc-900 bg-zinc-950"
    >
      <div className="container mx-auto flex max-w-5xl flex-col gap-4 px-4 py-8 md:flex-row md:items-center md:gap-4 md:px-6 md:py-10">
        <div className="flex items-center gap-2 md:shrink-0 md:border-r md:border-zinc-800 md:pr-4">
          <Sparkles className="h-4 w-4 shrink-0 text-indigo-400" aria-hidden />
          <div className="flex flex-col">
            <span className="font-mono text-xs uppercase tracking-wider text-indigo-400">
              What&apos;s new in v2.2.1
            </span>
            <span className="text-xs text-zinc-500">
              Protocol Hardening + real WebAuthn — released Apr 2026
            </span>
          </div>
        </div>

        <ul className="flex flex-wrap items-center gap-2">
          {PILLS.map((pill) => {
            const Icon = pill.icon;
            const linkProps = pill.external
              ? { target: '_blank', rel: 'noopener noreferrer' as const }
              : {};
            return (
              <li key={pill.label}>
                <Link
                  href={pill.href}
                  {...linkProps}
                  className="group inline-flex items-center gap-1.5 rounded-full border border-zinc-800 bg-zinc-900/50 px-3 py-1.5 text-xs font-medium text-zinc-400 backdrop-blur-sm transition-colors hover:border-indigo-500/40 hover:bg-indigo-500/10 hover:text-indigo-300"
                >
                  <Icon
                    className="h-3.5 w-3.5 text-zinc-500 transition-colors group-hover:text-indigo-400"
                    aria-hidden
                  />
                  <span>{pill.label}</span>
                  {pill.external ? (
                    <ArrowUpRight
                      className="h-3 w-3 text-zinc-600 transition-colors group-hover:text-indigo-400"
                      aria-hidden
                    />
                  ) : null}
                </Link>
              </li>
            );
          })}
        </ul>
      </div>
    </aside>
  );
}
