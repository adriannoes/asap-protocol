/**
 * Fixture endpoint for load testing: returns a configurable number of mock agents.
 * Only enabled when ENABLE_FIXTURE_ROUTES=true (e.g. in Playwright or local load tests).
 * Do not enable in production.
 */

import { NextRequest, NextResponse } from 'next/server';

const MAX_FIXTURE_AGENTS = 2000;

function buildFixtureAgents(count: number): Record<string, unknown>[] {
  const agents: Record<string, unknown>[] = [];
  const skillsPool = ['code_review', 'summarize', 'translate', 'search', 'analyze', 'synthesize'];
  for (let i = 0; i < count; i++) {
    const id = `urn:asap:agent:loadtest:agent-${i}`;
    const name = `Load Test Agent ${i}`;
    agents.push({
      id,
      name,
      description: `Fixture agent ${i} for client-side load testing. Simulates registry.json payload.`,
      endpoints: {
        asap: `https://example.com/agents/${i}/asap`,
        http: `https://example.com/agents/${i}/asap`,
      },
      skills: skillsPool.slice(0, 2 + (i % 3)),
      asap_version: '1.0',
      verification: i % 5 === 0 ? { status: 'verified' } : null,
    });
  }
  return agents;
}

export async function GET(request: NextRequest) {
  if (process.env.ENABLE_FIXTURE_ROUTES !== 'true') {
    return NextResponse.json({ error: 'Not available' }, { status: 404 });
  }

  const countParam = request.nextUrl.searchParams.get('count');
  const count = Math.min(
    Math.max(1, parseInt(countParam ?? '500', 10) || 500),
    MAX_FIXTURE_AGENTS
  );

  const agents = buildFixtureAgents(count);
  return NextResponse.json(agents, {
    headers: { 'Cache-Control': 'no-store' },
  });
}
