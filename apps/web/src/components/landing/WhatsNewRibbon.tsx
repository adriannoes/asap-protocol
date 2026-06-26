import Link from 'next/link';
import { WHATS_NEW_RIBBON_CTA_IDS } from '@/lib/telemetry/homepage-cta-ids';
import {
  Fingerprint,
  KeySquare,
  GitBranch,
  ShieldCheck,
  Sparkles,
  ArrowUpRight,
  Code,
  BookOpen,
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
  'https://github.com/adriannoes/asap-protocol/blob/main/CHANGELOG.md#251---2026-06-25';
const DOCS_MCP_AUTH_BRIDGE =
  'https://github.com/adriannoes/asap-protocol/blob/main/docs/adapters/mcp-auth-bridge.md';
const DOCS_MCP_INTEGRATION =
  'https://github.com/adriannoes/asap-protocol/blob/main/docs/mcp-integration.md';
const DOCS_MIGRATION_251 =
  'https://github.com/adriannoes/asap-protocol/blob/main/docs/migration.md#upgrading-from-v250-to-v251';
const EXAMPLE_MCP_AUTH_BRIDGE =
  'https://github.com/adriannoes/asap-protocol/tree/main/examples/mcp_auth_bridge';
const DOCS_TS_SDK =
  'https://github.com/adriannoes/asap-protocol/blob/main/docs/sdks/typescript.md';

const PILLS: Pill[] = [
  {
    label: 'MCP Auth Bridge',
    href: DOCS_MCP_AUTH_BRIDGE,
    icon: ShieldCheck,
    external: true,
    dataCta: WHATS_NEW_RIBBON_CTA_IDS.docsMcpAuthBridge,
  },
  {
    label: 'MCP modes',
    href: DOCS_MCP_INTEGRATION,
    icon: BookOpen,
    external: true,
    dataCta: WHATS_NEW_RIBBON_CTA_IDS.docsMcpIntegration,
  },
  {
    label: 'Example',
    href: EXAMPLE_MCP_AUTH_BRIDGE,
    icon: Sparkles,
    external: true,
    dataCta: WHATS_NEW_RIBBON_CTA_IDS.docsMcpAuthExample,
  },
  {
    label: 'Identity',
    href: '/features/per-agent-identity',
    icon: Fingerprint,
    dataCta: WHATS_NEW_RIBBON_CTA_IDS.featurePerAgentIdentity,
  },
  {
    label: 'Capabilities',
    href: '/features/scoped-capabilities',
    icon: KeySquare,
    dataCta: WHATS_NEW_RIBBON_CTA_IDS.featureScopedCapabilities,
  },
  {
    label: 'TypeScript SDK',
    href: DOCS_TS_SDK,
    icon: Code,
    external: true,
    dataCta: WHATS_NEW_RIBBON_CTA_IDS.docsTypescript,
  },
  {
    label: 'Migration',
    href: DOCS_MIGRATION_251,
    icon: BookOpen,
    external: true,
    dataCta: WHATS_NEW_RIBBON_CTA_IDS.docsMigration250,
  },
  {
    label: 'Changelog',
    href: CHANGELOG_URL,
    icon: GitBranch,
    external: true,
    dataCta: WHATS_NEW_RIBBON_CTA_IDS.releaseChangelogGithub,
  },
];

export function WhatsNewRibbon() {
  return (
    <aside
      aria-label="What's new in ASAP Protocol v2.5.1"
      className="w-full border-y border-zinc-900 bg-zinc-950"
    >
      <div className="container mx-auto flex max-w-5xl flex-col gap-4 px-4 py-8 md:flex-row md:items-center md:gap-4 md:px-6 md:py-10">
        <div className="flex items-center gap-2 md:shrink-0 md:border-r md:border-zinc-800 md:pr-4">
          <Sparkles className="h-4 w-4 shrink-0 text-indigo-400" aria-hidden />
          <div className="flex flex-col">
            <span className="font-mono text-xs uppercase tracking-wider text-indigo-400">
              What&apos;s new in v2.5.1
            </span>
            <span className="text-xs text-zinc-500">
              Code quality patch — June 2026
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
