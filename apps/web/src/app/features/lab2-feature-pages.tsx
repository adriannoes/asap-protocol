import type { ComponentType, ReactNode } from 'react';
import type { LucideIcon } from 'lucide-react';
import { Clock, FileCode, Globe, KeySquare, Lock, ShieldCheck, Workflow } from 'lucide-react';

import { EXTERNAL_LINK_FOCUS_CLASS, OpensInNewTabHint } from '@/components/links/opens-in-new-tab';
import { WHATS_NEW_RIBBON_CTA_IDS } from '@/lib/telemetry/homepage-cta-ids';
import { cn } from '@/lib/utils';

const DOCS_LINK =
  'rounded bg-zinc-800 px-1 py-0.5 text-sm text-indigo-300 underline-offset-2 hover:underline';

// Lab II docs/examples on main (v2.5.3).
const DOCS_WORKFLOW_CONNECTORS =
  'https://github.com/asap-protocol/asap-protocol/blob/main/docs/integrations/workflow-connectors.md';
const DOCS_AUTOMATION_CONNECTOR_SECURITY =
  'https://github.com/asap-protocol/asap-protocol/blob/main/docs/guides/automation-connector-security.md';
const EXAMPLE_WORKFLOW_CONNECTOR =
  'https://github.com/asap-protocol/asap-protocol/tree/main/examples/workflow_asap_connector';

export type FeatureCapability = { title: string; description: string; icon: LucideIcon };

export type FeaturePageContent = {
  title: string;
  description: string;
  icon: ComponentType<{ className?: string }>;
  content: ReactNode;
  capabilities: FeatureCapability[];
};

type DocsLinkProps = {
  href: string;
  /** Stable id for Vercel / site→docs CTR (required — avoids mute outbound links). */
  dataCta: string;
  children: ReactNode;
};

function DocsLink({ href, dataCta, children }: DocsLinkProps) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      data-cta={dataCta}
      className={cn(DOCS_LINK, EXTERNAL_LINK_FOCUS_CLASS)}
    >
      {children}
      <OpensInNewTabHint />
    </a>
  );
}

/** Adapter Lab II feature detail pages (workflow OpenAPI → ASAP skills). */
export const LAB2_FEATURE_PAGES: Record<
  'workflow-connectors' | 'automation-connector-security',
  FeaturePageContent
> = {
  'workflow-connectors': {
    title: 'Workflow Connectors',
    description:
      'Expose n8n-/Activepieces-style workflow HTTP APIs as ASAP skills via the OpenAPI adapter.',
    icon: Workflow,
    capabilities: [
      {
        title: 'OpenAPI → skills',
        description:
          'Map workflow-host REST operations to ASAP capabilities with create_from_openapi.',
        icon: FileCode,
      },
      {
        title: 'Agent-invoked proxy',
        description:
          'Remote agents invoke skills that proxy to the workflow host — not the reverse.',
        icon: Globe,
      },
      {
        title: 'Retry-aware',
        description: 'Documented patterns for timeouts, idempotency, and failure handling.',
        icon: Clock,
      },
    ],
    content: (
      <>
        <p className="mb-6">
          Workflow platforms already expose HTTPS APIs. The workflow connectors guide shows how to
          turn those OpenAPI operations into ASAP skills so remote agents can invoke them —
          envelopes, auth headers, and retry patterns — without forking the protocol. Agents call
          ASAP; the connector proxies to the workflow host (n8n, Activepieces, and similar).
        </p>
        <p className="mb-6">
          Docs:{' '}
          <DocsLink
            href={DOCS_WORKFLOW_CONNECTORS}
            dataCta={WHATS_NEW_RIBBON_CTA_IDS.docsWorkflowConnectors}
          >
            docs/integrations/workflow-connectors.md
          </DocsLink>
          . Runnable sample:{' '}
          <DocsLink
            href={EXAMPLE_WORKFLOW_CONNECTOR}
            dataCta={WHATS_NEW_RIBBON_CTA_IDS.docsWorkflowConnectorExample}
          >
            examples/workflow_asap_connector/
          </DocsLink>
          .
        </p>
      </>
    ),
  },
  'automation-connector-security': {
    title: 'Automation Connector Security',
    description: 'Harden OpenAPI-backed workflow connectors: secrets, least privilege, TLS.',
    icon: Lock,
    capabilities: [
      {
        title: 'Secrets hygiene',
        description:
          'Store tokens in env / secret stores — never hardcode in OpenAPI or manifests.',
        icon: KeySquare,
      },
      {
        title: 'Least privilege',
        description:
          'Scope capability grants for connector skills to the minimum required surface.',
        icon: ShieldCheck,
      },
      {
        title: 'MCP when exposed',
        description:
          'MCP Auth Bridge applies when a connector exposes MCP (e.g. NeMo Path A) — not the OpenAPI-only workflow example.',
        icon: Lock,
      },
    ],
    content: (
      <>
        <p className="mb-6">
          OpenAPI-backed workflow connectors move credentials and upstream calls across boundaries.
          This guide covers secrets management, least-privilege capability grants, HTTPS/TLS for
          live upstreams and webhooks, and rate limits. The primary workflow example is
          OpenAPI-only; use the MCP Auth Bridge when a connector exposes MCP tools (for example NeMo
          Path A), not as the default workflow pattern.
        </p>
        <p className="mb-6">
          Docs:{' '}
          <DocsLink
            href={DOCS_AUTOMATION_CONNECTOR_SECURITY}
            dataCta={WHATS_NEW_RIBBON_CTA_IDS.docsAutomationConnectorSecurity}
          >
            docs/guides/automation-connector-security.md
          </DocsLink>
          . Pair with{' '}
          <DocsLink
            href={DOCS_WORKFLOW_CONNECTORS}
            dataCta={WHATS_NEW_RIBBON_CTA_IDS.docsWorkflowConnectors}
          >
            docs/integrations/workflow-connectors.md
          </DocsLink>
          .
        </p>
      </>
    ),
  },
};
