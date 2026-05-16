import Link from 'next/link';
import {
  Fingerprint,
  KeySquare,
  GitBranch,
  Layers,
  ShieldCheck,
  Sparkles,
  ArrowUpRight,
  Code,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

type Pill = {
  label: string;
  href: string;
  icon: LucideIcon;
  external?: boolean;
  /** Stable id for analytics (Vercel / site→docs CTR). */
  dataCta: string;
};

const CHANGELOG_URL =
  'https://github.com/adriannoes/asap-protocol/blob/main/CHANGELOG.md#230---2026-05-04';
const DOCS_OPENAPI =
  'https://github.com/adriannoes/asap-protocol/blob/main/docs/adapters/openapi.md';
const DOCS_TS_SDK =
  'https://github.com/adriannoes/asap-protocol/blob/main/docs/sdks/typescript.md';
const DOCS_AUTO_REG =
  'https://github.com/adriannoes/asap-protocol/blob/main/docs/registry/auto-registration.md';
const DOCS_ESCALATION =
  'https://github.com/adriannoes/asap-protocol/blob/main/docs/capabilities/escalation.md';

const PILLS: Pill[] = [
  { label: 'OpenAPI', href: DOCS_OPENAPI, icon: Layers, external: true, dataCta: 'docs-openapi' },
  { label: 'TypeScript SDK', href: DOCS_TS_SDK, icon: Code, external: true, dataCta: 'docs-typescript' },
  { label: 'Auto-Reg', href: DOCS_AUTO_REG, icon: Sparkles, external: true, dataCta: 'docs-auto-registration' },
  {
    label: 'Identity',
    href: '/features/per-agent-identity',
    icon: Fingerprint,
    dataCta: 'feature-per-agent-identity',
  },
  {
    label: 'Capabilities',
    href: '/features/scoped-capabilities',
    icon: KeySquare,
    dataCta: 'feature-scoped-capabilities',
  },
  {
    label: 'Escalation',
    href: DOCS_ESCALATION,
    icon: ShieldCheck,
    external: true,
    dataCta: 'docs-capabilities-escalation',
  },
  { label: 'Changelog', href: CHANGELOG_URL, icon: GitBranch, external: true, dataCta: 'release-changelog-github' },
];

export function WhatsNewRibbon() {
  return (
    <aside
      aria-label="What's new in ASAP Protocol v2.3.0"
      className="w-full border-y border-zinc-900 bg-zinc-950"
    >
      <div className="container mx-auto flex max-w-5xl flex-col gap-4 px-4 py-8 md:flex-row md:items-center md:gap-4 md:px-6 md:py-10">
        <div className="flex items-center gap-2 md:shrink-0 md:border-r md:border-zinc-800 md:pr-4">
          <Sparkles className="h-4 w-4 shrink-0 text-indigo-400" aria-hidden />
          <div className="flex flex-col">
            <span className="font-mono text-xs uppercase tracking-wider text-indigo-400">
              What&apos;s new in v2.3.0
            </span>
            <span className="text-xs text-zinc-500">
              OpenAPI adapter, TypeScript SDK, auto-registration, escalation — May 2026
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
                  data-cta={pill.dataCta}
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
