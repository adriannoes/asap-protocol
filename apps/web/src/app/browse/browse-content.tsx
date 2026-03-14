'use client';

import { Suspense, useState, useMemo } from 'react';
import type { RegistryAgent } from '@/types/registry';
import { Badge } from '@/components/ui/badge';
import { Search } from 'lucide-react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';
import { DataTable } from '@/components/agents/data-table';
import { columns } from '@/components/agents/columns';

function DataTableSkeleton() {
    return (
        <div className="w-full space-y-4" data-testid="data-table-skeleton">
            <Skeleton className="h-9 w-full sm:max-w-sm" />
            <Skeleton className="h-[400px] w-full rounded-md" />
            <div className="flex justify-between">
                <Skeleton className="h-4 w-24" />
                <div className="flex gap-2">
                    <Skeleton className="h-8 w-20" />
                    <Skeleton className="h-8 w-16" />
                </div>
            </div>
        </div>
    );
}

interface BrowseContentProps {
    initialAgents: RegistryAgent[];
}

export function BrowseContent({ initialAgents }: BrowseContentProps) {
    const [selectedCategory, setSelectedCategory] = useState<string>('');
    const [selectedTags, setSelectedTags] = useState<string[]>([]);
    const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
    const [requireSla, setRequireSla] = useState(false);
    const [requireAuth, setRequireAuth] = useState(false);

    // Extract unique categories (Task 4.4.2)
    const availableCategories = useMemo(() => {
        const categoriesSet = new Set<string>();
        initialAgents.forEach((agent) => {
            if (agent.category) categoriesSet.add(agent.category);
        });
        return Array.from(categoriesSet).sort();
    }, [initialAgents]);

    const availableTags = useMemo(() => {
        const tagsSet = new Set<string>();
        initialAgents.forEach((agent) => {
            if (Array.isArray(agent.tags)) {
                agent.tags.forEach((tag) => {
                    if (tag) tagsSet.add(tag);
                });
            }
        });
        return Array.from(tagsSet).sort();
    }, [initialAgents]);

    const availableSkills = useMemo(() => {
        const skillsSet = new Set<string>();
        initialAgents.forEach((agent) => {
            if (Array.isArray(agent.capabilities?.skills)) {
                agent.capabilities.skills.forEach((skill: { id: string }) => {
                    if (skill.id) skillsSet.add(skill.id);
                });
            }
        });
        return Array.from(skillsSet).sort();
    }, [initialAgents]);

    const toggleSkill = (skill: string) => {
        setSelectedSkills((prev) =>
            prev.includes(skill)
                ? prev.filter((s) => s !== skill)
                : [...prev, skill]
        );
    };

    const toggleTag = (tag: string) => {
        setSelectedTags((prev) =>
            prev.includes(tag)
                ? prev.filter((t) => t !== tag)
                : [...prev, tag]
        );
    };

    // Filter agents based on sidebar filters (search is handled by DataTable)
    const filteredAgents = useMemo(() => {
        let result = initialAgents;

        // Apply Skills Filter (Strict Mode)
        if (selectedSkills.length > 0) {
            result = result.filter((agent) => {
                const agentSkills = Array.isArray(agent.capabilities?.skills)
                    ? agent.capabilities.skills.map((s: { id: string }) => s.id)
                    : [];

                return selectedSkills.every((skill) => agentSkills.includes(skill));
            });
        }

        if (requireSla) {
            result = result.filter((agent) => !!agent.sla);
        }

        if (requireAuth) {
            result = result.filter((agent) => Array.isArray(agent.auth?.schemes) && agent.auth.schemes.length > 0);
        }

        if (selectedCategory) {
            result = result.filter((agent) => agent.category === selectedCategory);
        }

        if (selectedTags.length > 0) {
            result = result.filter((agent) => {
                const agentTags = Array.isArray(agent.tags) ? agent.tags : [];
                return selectedTags.every((tag) => agentTags.includes(tag));
            });
        }

        return result;
    }, [initialAgents, selectedSkills, selectedCategory, selectedTags, requireSla, requireAuth]);

    return (
        <div className="flex flex-col md:flex-row gap-6">
            <div className="w-full md:w-64 shrink-0 space-y-6">
                <div className="rounded-lg border bg-card text-card-foreground shadow-sm p-4">
                    <h2 className="font-semibold mb-4">Filters</h2>
                    <div className="space-y-4">
                        {/* Category Filter (Task 4.4.2) — Shadcn Select per tech-stack */}
                        <div className="pt-4 border-t">
                            <h3 className="text-sm font-medium mb-3">Category</h3>
                            <Select
                                value={selectedCategory || '__all__'}
                                onValueChange={(v) => setSelectedCategory(v === '__all__' ? '' : v)}
                            >
                                <SelectTrigger className="w-full">
                                    <SelectValue placeholder="All Categories" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="__all__">All Categories</SelectItem>
                                    {availableCategories.map((cat) => (
                                        <SelectItem key={cat} value={cat}>
                                            {cat}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="pt-4 border-t">
                            <h3 className="text-sm font-medium mb-3">Tags</h3>
                            {availableTags.length > 0 ? (
                                <div className="flex flex-wrap gap-2">
                                    {availableTags.map((tag) => {
                                        const isSelected = selectedTags.includes(tag);
                                        return (
                                            <Badge
                                                key={tag}
                                                variant={isSelected ? 'default' : 'outline'}
                                                className={cn(
                                                    "cursor-pointer transition-colors",
                                                    isSelected ? "hover:bg-primary/80" : "hover:bg-muted"
                                                )}
                                                onClick={() => toggleTag(tag)}
                                            >
                                                {tag}
                                            </Badge>
                                        );
                                    })}
                                </div>
                            ) : (
                                <p className="text-xs text-muted-foreground italic">No tags found.</p>
                            )}
                        </div>

                        <div className="pt-4 border-t">
                            <h3 className="text-sm font-medium mb-3">Skills</h3>
                            {availableSkills.length > 0 ? (
                                <div className="flex flex-wrap gap-2">
                                    {availableSkills.map((skill) => {
                                        const isSelected = selectedSkills.includes(skill);
                                        return (
                                            <Badge
                                                key={skill}
                                                variant={isSelected ? 'default' : 'outline'}
                                                className={cn(
                                                    "cursor-pointer transition-colors",
                                                    isSelected ? "hover:bg-primary/80" : "hover:bg-muted"
                                                )}
                                                onClick={() => toggleSkill(skill)}
                                            >
                                                {skill}
                                            </Badge>
                                        );
                                    })}
                                </div>
                            ) : (
                                <p className="text-xs text-muted-foreground italic">No skills found in registry.</p>
                            )}
                        </div>

                        <div className="pt-4 border-t">
                            <h3 className="text-sm font-medium mb-3">Trust Levels</h3>
                            <div className="space-y-2">
                                <label className="flex items-center space-x-2 cursor-pointer group">
                                    <input
                                        type="checkbox"
                                        className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-600 bg-transparent"
                                        checked={requireSla}
                                        onChange={(e) => setRequireSla(e.target.checked)}
                                    />
                                    <span className="text-sm text-foreground group-hover:text-indigo-400 transition-colors">Has published SLA</span>
                                </label>
                                <label className="flex items-center space-x-2 cursor-pointer group">
                                    <input
                                        type="checkbox"
                                        className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-600 bg-transparent"
                                        checked={requireAuth}
                                        onChange={(e) => setRequireAuth(e.target.checked)}
                                    />
                                    <span className="text-sm text-foreground group-hover:text-indigo-400 transition-colors">Requires Authentication</span>
                                </label>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Main Content / DataTable */}
            <div className="flex-1">
                {filteredAgents.length === 0 ? (
                    <div className="rounded-xl border border-dashed border-zinc-800 bg-zinc-950 p-12 flex flex-col items-center justify-center text-center relative overflow-hidden group">
                        <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:14px_24px] pointer-events-none" />
                        <div className="relative z-10 flex flex-col items-center max-w-md">
                            <div className="h-12 w-12 rounded-lg bg-zinc-900 border border-zinc-800 flex items-center justify-center mb-6">
                                <Search className="h-6 w-6 text-zinc-500" />
                            </div>
                            <h3 className="mb-3 text-xl font-medium tracking-tight text-white">No agents match your criteria</h3>
                            <p className="mb-6 text-sm text-zinc-400 leading-relaxed">
                                There are currently no agents that match your selected filters. Try broadening your search criteria.
                            </p>
                            <Button asChild variant="outline" className="border-zinc-800 text-zinc-300 hover:bg-zinc-900 hover:text-white">
                                <Link href="/dashboard/register">Register an Agent</Link>
                            </Button>
                        </div>
                    </div>
                ) : (
                    <Suspense fallback={<DataTableSkeleton />}>
                        <DataTable columns={columns} data={filteredAgents} searchKey="name" />
                    </Suspense>
                )}
            </div>
        </div>
    );
}
