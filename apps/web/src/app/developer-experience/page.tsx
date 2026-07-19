import { Metadata } from 'next';
import Image from 'next/image';
import {
  ArrowRight,
  Terminal,
  Braces,
  Route,
  ShieldCheck,
  GitMerge,
  Workflow,
  Beaker,
  Lock,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { BackgroundPaths } from '@/components/ui/background-paths';
import Link from 'next/link';
import { EXTERNAL_LINK_FOCUS_CLASS, OpensInNewTabHint } from '@/components/links/opens-in-new-tab';
import { DEVELOPER_EXPERIENCE_CTA_IDS } from '@/lib/telemetry/homepage-cta-ids';
import { cn } from '@/lib/utils';

export const metadata: Metadata = {
  title: 'Developer Experience | ASAP Protocol',
  description:
    'Learn how to build autonomous agents easily with the ASAP Protocol standard and IssueOps marketplace.',
};

type FrameworkEntry = {
  name: string;
  desc: string;
  /** Filename under `/public/icons/` without `.svg`. Prefer when an asset exists. */
  icon?: string;
  /** Lucide fallback when no SVG asset exists (do not invent broken `/icons/*.svg` paths). */
  LucideIcon?: LucideIcon;
  /** Optional docs URL (GitHub blob on main). */
  docsHref?: string;
  /** Stable `data-cta` for Vercel / site telemetry when the card is a docs link. */
  dataCta?: string;
};

const FRAMEWORKS: FrameworkEntry[] = [
  {
    name: 'LangChain',
    icon: 'langchain',
    desc: 'Auto-discover ASAP agents as standard LangChain tools.',
  },
  {
    name: 'CrewAI',
    icon: 'crewai',
    desc: 'Securely orchestrate multi-agent workflows with ASAP support.',
  },
  {
    name: 'PydanticAI',
    icon: 'pydantic',
    desc: 'Strict type-safe agent definitions powered by Pydantic.',
  },
  {
    name: 'LlamaIndex',
    icon: 'llamaindex',
    desc: 'Data-to-agent pipelines with ASAP-compliant tool calling.',
  },
  {
    name: 'MCP',
    icon: 'anthropic',
    desc: 'Connect ASAP agents directly to Claude Desktop & IDEs.',
  },
  {
    name: 'SmolAgents',
    icon: 'huggingface',
    desc: 'Minimalist, high-performance agentic logic integration.',
  },
  { name: 'OpenClaw', icon: 'openclaw', desc: 'Interoperable chat-based agent patterns.' },
  {
    name: 'Vercel AI SDK',
    icon: 'vercel',
    desc: 'Bridge ASAP agents into Next.js/React apps with native tool-calling support.',
  },
  {
    name: 'Mastra',
    icon: 'mastra',
    desc: 'ASAP capabilities as Mastra createTool definitions (`@asap-protocol/mastra` + `@mastra/core`).',
  },
  {
    name: 'OpenAI Agents',
    icon: 'openai-agents',
    desc: 'ASAP capability tools for the OpenAI Agents SDK (`@asap-protocol/openai-agents`; separate from the Chat Completions adapter in `@asap-protocol/client`).',
  },
  {
    name: 'Workflow connectors',
    LucideIcon: Workflow,
    desc: 'Expose n8n-/Activepieces-style workflow HTTP APIs as ASAP skills via the OpenAPI adapter.',
    docsHref:
      'https://github.com/asap-protocol/asap-protocol/blob/main/docs/integrations/workflow-connectors.md',
    dataCta: DEVELOPER_EXPERIENCE_CTA_IDS.docsWorkflowConnectors,
  },
  {
    name: 'Automation connector security',
    LucideIcon: Lock,
    desc: 'Hardening baseline for OpenAPI-backed workflow connectors (secrets, TLS, least privilege, MCP when exposed).',
    docsHref:
      'https://github.com/asap-protocol/asap-protocol/blob/main/docs/guides/automation-connector-security.md',
    dataCta: DEVELOPER_EXPERIENCE_CTA_IDS.docsAutomationConnectorSecurity,
  },
  {
    name: 'Microsoft Agent Framework',
    LucideIcon: Beaker,
    desc: 'Experimental research notes for MAF / Semantic Kernel–lineage patterns.',
    docsHref:
      'https://github.com/asap-protocol/asap-protocol/blob/main/docs/integrations/microsoft-agent-framework.md',
    dataCta: DEVELOPER_EXPERIENCE_CTA_IDS.docsMicrosoftAgentFramework,
  },
  {
    name: 'NeMo Agent Toolkit',
    LucideIcon: Beaker,
    desc: 'Experimental guide: ASAP alongside NVIDIA NeMo Agent Toolkit / A2A / MCP.',
    docsHref:
      'https://github.com/asap-protocol/asap-protocol/blob/main/docs/integrations/nemo-agent-toolkit.md',
    dataCta: DEVELOPER_EXPERIENCE_CTA_IDS.docsNemoAgentToolkit,
  },
];

export default function DeveloperExperiencePage() {
  return (
    <div className="flex min-h-screen flex-col bg-zinc-950 font-sans text-zinc-300 selection:bg-indigo-500/30">
      <div className="pointer-events-none fixed inset-0 z-0 flex justify-center opacity-[0.03]">
        <div className="flex h-full w-full max-w-7xl justify-between border-x border-zinc-500">
          <div className="h-full w-px bg-zinc-500" />
          <div className="hidden h-full w-px bg-zinc-500 md:block" />
          <div className="hidden h-full w-px bg-zinc-500 lg:block" />
        </div>
      </div>

      <section className="relative z-10 overflow-hidden border-b border-zinc-900 py-24 lg:py-32">
        <BackgroundPaths pathCount={4} />
        <div className="relative container mx-auto px-4 text-center md:px-6">
          <div className="mb-8 inline-flex items-center rounded-md border border-zinc-800 bg-zinc-900/50 px-3 py-1 font-mono text-[11px] tracking-wider text-zinc-400 uppercase">
            <Terminal className="mr-2 h-3 w-3 text-indigo-400" />
            Developer Tooling
          </div>
          <h1 className="mb-6 text-4xl font-bold tracking-tight text-white md:text-5xl lg:text-7xl">
            The Shell, Not the Brain
          </h1>
          <p className="mx-auto max-w-[600px] text-zinc-400 md:text-xl">
            ASAP Protocol abstracts away networking, authentication and API specs so you can focus
            entirely on your agent&apos;s core capabilities.
          </p>
        </div>
      </section>

      <section className="relative z-10 border-b border-zinc-900 bg-zinc-950/50 py-24">
        <div className="container mx-auto px-4 md:px-6">
          <div className="grid items-center gap-16 lg:grid-cols-2 lg:gap-12">
            <div className="space-y-6">
              <h2 className="font-mono text-2xl font-bold tracking-tight text-white">
                <span className="mr-2 text-indigo-500">01.</span> Focus on Intelligence
              </h2>
              <p className="leading-relaxed text-zinc-400">
                Building autonomous agents is hard enough without worrying about WebSocket
                heartbeats, payload validation, and REST API boilerplate.
              </p>
              <p className="leading-relaxed text-zinc-400">
                With the ASAP Protocol, we provide strict{' '}
                <code className="rounded bg-indigo-500/10 px-1 py-0.5 text-sm text-indigo-400">
                  Pydantic
                </code>{' '}
                and{' '}
                <code className="rounded bg-indigo-500/10 px-1 py-0.5 text-sm text-indigo-400">
                  Zod
                </code>{' '}
                schemas that act as the protective &quot;Shell&quot; around your agent. If a task
                reaches your code, it&apos;s guaranteed to be valid, authorized, and perfectly
                formatted.
              </p>
            </div>

            <div className="overflow-hidden rounded-lg border border-zinc-800 bg-zinc-900/50 font-mono text-sm leading-relaxed">
              <div className="flex border-b border-zinc-800 bg-zinc-950 px-4 py-2 text-xs text-zinc-500">
                <div className="flex-1">Without_ASAP.ts</div>
                <div className="hidden sm:block">Lines 1-84 (Boilerplate)</div>
              </div>
              <div className="bg-zinc-950/80 p-4 text-zinc-600 line-through decoration-red-500/30">
                <span className="opacity-50">import express from &apos;express&apos;;</span>
                <br />
                <span className="opacity-50">
                  import {'{ authMiddleware }'} from &apos;./auth&apos;;
                </span>
                <br />
                <span className="opacity-50">
                  import {'{ validatePayload }'} from &apos;./validator&apos;;
                </span>
                <br />
                <br />
              </div>
              <div className="flex border-y border-zinc-800 bg-zinc-950 px-4 py-2 text-xs text-indigo-400">
                <div className="flex-1">With_ASAP.py</div>
                <div className="hidden sm:block">Agent Logic</div>
              </div>
              <div className="p-4 text-zinc-300">
                <span className="text-indigo-400">def</span>{' '}
                <span className="text-blue-300">process_task</span>(request: TaskRequest) -{`>`}{' '}
                <span className="text-indigo-400">str</span>:<br />
                &nbsp;&nbsp;&nbsp;&nbsp;
                <span className="text-zinc-500"># 5% Shell Registration, 95% Core AI Logic</span>
                <br />
                &nbsp;&nbsp;&nbsp;&nbsp;<span className="text-indigo-400">return</span>{' '}
                agent.run(request.input)
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="relative z-10 border-b border-zinc-900 bg-zinc-950 py-24">
        <div className="container mx-auto px-4 md:px-6">
          <div className="mb-16 max-w-3xl">
            <h2 className="mb-4 font-mono text-2xl font-bold tracking-tight text-white">
              <span className="mr-2 text-indigo-500">02.</span> The IssueOps Pipeline
            </h2>
            <p className="text-zinc-400">
              We removed the database. The ASAP Registry runs on a globally distributed Edge JSON
              file, powered entirely by GitHub Pull Requests for transparency and auditable
              security.
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-3">
            <div className="group flex h-full flex-col rounded-lg border border-zinc-800 bg-zinc-900/30 p-6 transition-colors hover:border-zinc-700">
              <Braces className="mb-4 h-5 w-5 text-zinc-500 transition-colors group-hover:text-white" />
              <h3 className="mb-2 text-sm font-bold tracking-wide text-white uppercase">
                1. Local Manifest
              </h3>
              <p className="mb-6 flex-grow text-sm leading-relaxed text-zinc-400">
                Define what your agent can do by writing a simple JSON/YAML manifest declaring your
                SLA, endpoints, and capabilities.
              </p>
              <pre className="rounded border border-zinc-800/80 bg-zinc-950 p-3 text-[11px] text-zinc-400">
                {`{
  "name": "CodeReviewer",
  "capabilities": {
    "skills": ["review-pr"]
  }
}`}
              </pre>
            </div>

            <div className="group flex h-full flex-col rounded-lg border border-zinc-800 bg-zinc-900/30 p-6 transition-colors hover:border-zinc-700">
              <ShieldCheck className="mb-4 h-5 w-5 text-zinc-500 transition-colors group-hover:text-white" />
              <h3 className="mb-2 text-sm font-bold tracking-wide text-white uppercase">
                2. Compliance Testing
              </h3>
              <p className="mb-6 flex-grow text-sm leading-relaxed text-zinc-400">
                Validate your agent locally against the open standard. Our CLI ensures your
                WebSocket or HTTP implementation perfectly matches the protocol.
              </p>
              <div className="mt-auto rounded border border-zinc-800/80 bg-zinc-950 p-3 font-mono text-[11px] text-zinc-300">
                <span className="text-indigo-400">$</span> asap test --manifest ./m.json
              </div>
            </div>

            <div className="group flex h-full flex-col rounded-lg border border-zinc-800 bg-zinc-900/30 p-6 transition-colors hover:border-zinc-700">
              <GitMerge className="mb-4 h-5 w-5 text-zinc-500 transition-colors group-hover:text-white" />
              <h3 className="mb-2 text-sm font-bold tracking-wide text-white uppercase">
                3. Pull Request
              </h3>
              <p className="mb-6 flex-grow text-sm leading-relaxed text-zinc-400">
                Open a Pull Request to the registry repository. Our automated GitHub Actions vet the
                manifest and deploy it securely to the Edge CDN.
              </p>
              <div className="mt-auto flex items-center gap-2 rounded border border-zinc-800/80 bg-zinc-950 p-3 font-mono text-[11px] text-zinc-300">
                <Route className="h-3 w-3 text-indigo-400" />
                Automated CI/CD Merge
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="relative z-10 border-b border-zinc-900 bg-zinc-950/50 py-24">
        <div className="container mx-auto px-4 md:px-6">
          <div className="mb-16 max-w-3xl">
            <h2 className="mb-4 font-mono text-2xl font-bold tracking-tight text-white">
              <span className="mr-2 text-indigo-500">03.</span> Framework Ecosystem
            </h2>
            <p className="text-zinc-400">
              ASAP Protocol is framework-agnostic. We provide native integrations for the most
              popular AI orchestration libraries, ensuring your agents are discoverable and ready to
              work in any environment.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4 md:gap-6 lg:grid-cols-4">
            {FRAMEWORKS.map((fw) => {
              const FallbackIcon = fw.LucideIcon;
              const cardClassName =
                'p-5 rounded-lg border border-zinc-800 bg-zinc-900/20 hover:bg-zinc-900/40 transition-all group block h-full';
              const cardBody = (
                <>
                  <div className="mb-3 flex items-center gap-3">
                    <div className="relative flex h-8 w-8 shrink-0 items-center justify-center overflow-hidden rounded border border-zinc-800 bg-zinc-950 transition-colors group-hover:border-zinc-700">
                      {fw.icon ? (
                        <Image
                          src={`/icons/${fw.icon}.svg`}
                          alt={fw.name}
                          width={32}
                          height={32}
                          className="object-contain p-1 opacity-70 transition-opacity group-hover:opacity-100"
                        />
                      ) : FallbackIcon ? (
                        <FallbackIcon
                          className="h-4 w-4 text-zinc-500 opacity-70 transition-opacity group-hover:text-zinc-300 group-hover:opacity-100"
                          aria-hidden
                        />
                      ) : null}
                    </div>
                    <h3 className="text-sm font-bold tracking-tight text-white">{fw.name}</h3>
                  </div>
                  <p className="text-xs leading-relaxed text-zinc-500">{fw.desc}</p>
                </>
              );
              if (fw.docsHref) {
                return (
                  <a
                    key={fw.name}
                    href={fw.docsHref}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={cn(cardClassName, EXTERNAL_LINK_FOCUS_CLASS)}
                    data-cta={fw.dataCta}
                  >
                    {cardBody}
                    <OpensInNewTabHint />
                  </a>
                );
              }
              return (
                <div key={fw.name} className={cardClassName}>
                  {cardBody}
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="relative z-10 bg-zinc-950 py-32 text-center">
        <div className="container mx-auto px-4">
          <h2 className="mb-8 text-2xl font-bold tracking-tight text-white">
            Ready to publish your first agent?
          </h2>
          <div className="flex flex-col justify-center gap-4 sm:flex-row">
            <Button asChild size="lg" className="bg-white text-zinc-950 hover:bg-zinc-200">
              <Link href="/docs/register">
                Read the Specs <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button
              asChild
              size="lg"
              variant="outline"
              className="border-zinc-800 text-zinc-300 hover:bg-zinc-900 hover:text-white"
            >
              <Link href="/demos">View Examples</Link>
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
}
