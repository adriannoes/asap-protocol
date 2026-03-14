'use client';
import { useEffect, useState } from 'react';
import { BrowseContent } from '../browse-content';
import BrowseLoading from '../loading';
import type { Manifest } from '@/types/protocol';

const FIXTURE_COUNT = 500;
const FIXTURE_URL = `/api/fixtures/registry?count=${FIXTURE_COUNT}`;

export default function BrowseLoadTestPage() {
  const [agents, setAgents] = useState<Manifest[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    fetch(FIXTURE_URL)
      .then((res) => {
        if (!res.ok) throw new Error(`Fixture failed: ${res.status}`);
        return res.json();
      })
      .then((data: unknown) => {
        if (cancelled) return;
        const list = Array.isArray(data) ? data : (data as { agents?: unknown[] }).agents ?? [];
        setAgents(list as Manifest[]);
        if (typeof performance !== 'undefined' && performance.mark) {
          performance.mark('load-test-agents-rendered');
        }
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return <BrowseLoading />;
  }

  if (error) {
    return (
      <div className="container mx-auto py-10 px-4 max-w-7xl">
        <p className="text-destructive">Fixture unavailable: {error}</p>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-10 px-4 max-w-7xl">
      <div className="flex flex-col space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Agent Registry (Load Test)</h1>
          <p className="text-muted-foreground mt-2">
            Browse and connect with verified autonomous agents. Currently tracking {agents.length} agents.
          </p>
        </div>
        <BrowseContent initialAgents={agents} />
      </div>
    </div>
  );
}
