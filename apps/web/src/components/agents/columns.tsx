'use client';

import type { ColumnDef } from '@tanstack/react-table';
import { ArrowUpDown } from 'lucide-react';
import Link from 'next/link';
import type { RegistryAgent } from '@/types/registry';
import type { Skill } from '@/types/protocol';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

/** Monochromatic badge style per design-system §8.3 */
const BADGE_MONO_CLASS = 'bg-black/5 dark:bg-white/10 backdrop-blur-sm border-0';

function getStatusDisplay(agent: RegistryAgent): string {
  const status = agent.verification?.status;
  if (status === 'verified') return 'Verified';
  if (status === 'rejected') return 'Rejected';
  return 'Pending';
}

function getSkillsList(agent: RegistryAgent): string[] {
  const skills = agent.capabilities?.skills;
  if (!Array.isArray(skills)) return [];
  return skills.map((s: Skill) => s.id);
}

export const columns: ColumnDef<RegistryAgent>[] = [
  {
    accessorKey: 'name',
    header: ({ column }) => (
      <Button
        variant="ghost"
        onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
        className="-ml-3"
      >
        Name
        <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
    cell: ({ row }) => {
      const agent = row.original;
      return (
        <Link
          href={`/agents/${encodeURIComponent(agent.id ?? '')}`}
          className="font-semibold hover:underline"
        >
          {agent.name ?? '—'}
        </Link>
      );
    },
  },
  {
    id: 'status',
    accessorFn: (row) => getStatusDisplay(row),
    header: ({ column }) => (
      <Button
        variant="ghost"
        onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
        className="-ml-3"
      >
        Status
        <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
    cell: ({ row }) => {
      const agent = row.original;
      const status = getStatusDisplay(agent);
      return (
        <Badge variant="outline" className={cn(BADGE_MONO_CLASS)}>
          {status}
        </Badge>
      );
    },
  },
  {
    id: 'version',
    accessorFn: (row) => row.capabilities?.asap_version ?? row.version ?? '2.0',
    header: 'Version',
    cell: ({ row }) => {
      const agent = row.original;
      const version = agent.capabilities?.asap_version ?? agent.version ?? '2.0';
      return <span className="font-mono text-sm">v{version}</span>;
    },
  },
  {
    id: 'skills',
    accessorFn: (row) => getSkillsList(row).join(', '),
    header: 'Skills',
    cell: ({ row }) => {
      const skills = getSkillsList(row.original);
      if (skills.length === 0) {
        return <span className="text-xs italic text-muted-foreground">—</span>;
      }
      return (
        <div className="flex flex-wrap gap-1">
          {skills.slice(0, 3).map((skill) => (
            <Badge
              key={skill}
              variant="outline"
              className={cn('text-xs', BADGE_MONO_CLASS)}
            >
              {skill}
            </Badge>
          ))}
          {skills.length > 3 && (
            <Badge variant="outline" className={cn('text-xs', BADGE_MONO_CLASS)}>
              +{skills.length - 3}
            </Badge>
          )}
        </div>
      );
    },
  },
];
