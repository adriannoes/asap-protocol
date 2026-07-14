/**
 * Stable homepage `data-cta` ids for Vercel analytics and `/api/telemetry`.
 * Keep landing components aligned with these constants to avoid dashboard drift.
 */

export const HOMEPAGE_HERO_CTA_IDS = {
  releaseBadge: 'hero-release-badge',
  exploreAgents: 'hero-explore-agents',
  registerAgent: 'hero-register-agent',
} as const;

/** CTA ids used by the “What’s new” ribbon (subset also appears in {@link HOMEPAGE_CTA_IDS}). */
export const WHATS_NEW_RIBBON_CTA_IDS = {
  docsMcpAuthBridge: 'docs-mcp-auth-bridge',
  docsMcpIntegration: 'docs-mcp-integration',
  docsMcpAuthExample: 'docs-mcp-auth-example',
  docsMigration250: 'docs-migration-250',
  docsOpenapi: 'docs-openapi',
  docsTypescript: 'docs-typescript',
  docsWorkflowConnectors: 'docs-workflow-connectors',
  docsAutomationConnectorSecurity: 'docs-automation-connector-security',
  docsMicrosoftAgentFramework: 'docs-microsoft-agent-framework',
  docsNemoAgentToolkit: 'docs-nemo-agent-toolkit',
  docsMastraIntegration: 'docs-mastra-integration',
  docsOpenaiAgentsIntegration: 'docs-openai-agents-integration',
  docsAutoRegistration: 'docs-auto-registration',
  featurePerAgentIdentity: 'feature-per-agent-identity',
  featureScopedCapabilities: 'feature-scoped-capabilities',
  docsCapabilitiesEscalation: 'docs-capabilities-escalation',
  releaseChangelogGithub: 'release-changelog-github',
} as const;

/** Lab II docs CTAs on `/developer-experience` (reuse ribbon ids where shared). */
export const DEVELOPER_EXPERIENCE_CTA_IDS = {
  docsWorkflowConnectors: WHATS_NEW_RIBBON_CTA_IDS.docsWorkflowConnectors,
  docsAutomationConnectorSecurity: WHATS_NEW_RIBBON_CTA_IDS.docsAutomationConnectorSecurity,
  docsMicrosoftAgentFramework: WHATS_NEW_RIBBON_CTA_IDS.docsMicrosoftAgentFramework,
  docsNemoAgentToolkit: WHATS_NEW_RIBBON_CTA_IDS.docsNemoAgentToolkit,
} as const;

/** Slugs from `/features/[slug]` cards — order matches the homepage grid. */
export const LANDING_FEATURE_SLUGS = [
  'openapi-adapter',
  'workflow-connectors',
  'automation-connector-security',
  'typescript-sdk',
  'mastra-adapter',
  'openai-agents-adapter',
  'auto-registration',
  'lite-registry',
  'verified-trust',
  '1-click-integration',
  'full-observability',
  'per-agent-identity',
  'scoped-capabilities',
  'streaming-responses',
] as const;

/** Ordered shell keys returned by `/api/telemetry` (`ctr_per_cta`). */
export const HOMEPAGE_CTA_IDS = [
  HOMEPAGE_HERO_CTA_IDS.releaseBadge,
  HOMEPAGE_HERO_CTA_IDS.exploreAgents,
  HOMEPAGE_HERO_CTA_IDS.registerAgent,
  WHATS_NEW_RIBBON_CTA_IDS.docsMcpAuthBridge,
  WHATS_NEW_RIBBON_CTA_IDS.docsMcpIntegration,
  WHATS_NEW_RIBBON_CTA_IDS.docsMcpAuthExample,
  WHATS_NEW_RIBBON_CTA_IDS.docsMigration250,
  WHATS_NEW_RIBBON_CTA_IDS.docsTypescript,
  WHATS_NEW_RIBBON_CTA_IDS.docsWorkflowConnectors,
  WHATS_NEW_RIBBON_CTA_IDS.docsAutomationConnectorSecurity,
  WHATS_NEW_RIBBON_CTA_IDS.docsMicrosoftAgentFramework,
  WHATS_NEW_RIBBON_CTA_IDS.docsNemoAgentToolkit,
  ...LANDING_FEATURE_SLUGS.map((slug) => `feature-${slug}` as const),
  WHATS_NEW_RIBBON_CTA_IDS.releaseChangelogGithub,
] as const;
