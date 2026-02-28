'use client';

import { useState, useMemo, useDeferredValue, useRef, useEffect } from 'react';
import { useWindowVirtualizer } from '@tanstack/react-virtual';
import type { RegistryAgent } from '@/types/registry';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Search, ShieldCheck } from 'lucide-react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

/** Breakpoints aligned with Tailwind: sm 640, md 768, lg 1024, xl 1280. */
function useColumns(): number {
    const [columns, setColumns] = useState(1);
    useEffect(() => {
        const update = () => {
            const w = typeof window !== 'undefined' ? window.innerWidth : 1280;
            setColumns(w >= 1280 ? 3 : w >= 1024 ? 2 : 1);
        };
        update();
        window.addEventListener('resize', update);
        return () => window.removeEventListener('resize', update);
    }, []);
    return columns;
}

interface BrowseContentProps {
    initialAgents: RegistryAgent[];
}

export function BrowseContent({ initialAgents }: BrowseContentProps) {
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedCategory, setSelectedCategory] = useState<string>('');
    const [selectedTags, setSelectedTags] = useState<string[]>([]);
    const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
    const [requireSla, setRequireSla] = useState(false);
    const [requireAuth, setRequireAuth] = useState(false);

    // Defer filter updates to keep UI responsive with 500+ entries (avoids blocking input)
    const deferredSearch = useDeferredValue(searchQuery);

    // Extract unique categories (Task 4.4.2)
    const availableCategories = useMemo(() => {
        const categoriesSet = new Set<string>();
        initialAgents.forEach((agent) => {
            if (agent.category) categoriesSet.add(agent.category);
        });
        return Array.from(categoriesSet).sort();
    }, [initialAgents]);

    // Extract unique tags (Task 4.4.3)
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

    // Extract unique skills from all agents (Task 4.1.3)
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

    // Filter agents based on search, selected skills, and trust levels
    const filteredAgents = useMemo(() => {
        let result = initialAgents;

        // Apply Search Filter (deferred to avoid blocking input)
        if (deferredSearch) {
            const lowerQuery = deferredSearch.toLowerCase();
            result = result.filter(
                (agent) =>
                    agent.name?.toLowerCase().includes(lowerQuery) ||
                    agent.description?.toLowerCase().includes(lowerQuery) ||
                    agent.id?.toLowerCase().includes(lowerQuery)
            );
        }

        // Apply Skills Filter (Strict Mode)
        if (selectedSkills.length > 0) {
            result = result.filter((agent) => {
                const agentSkills = Array.isArray(agent.capabilities?.skills)
                    ? agent.capabilities.skills.map((s: { id: string }) => s.id)
                    : [];

                return selectedSkills.every((skill) => agentSkills.includes(skill));
            });
        }

        // Apply Trust Level Filters (Task 4.1.4)
        if (requireSla) {
            result = result.filter((agent) => !!agent.sla);
        }

        if (requireAuth) {
            result = result.filter((agent) => Array.isArray(agent.auth?.schemes) && agent.auth.schemes.length > 0);
        }

        // Apply Category Filter (Task 4.4.2)
        if (selectedCategory) {
            result = result.filter((agent) => agent.category === selectedCategory);
        }

        // Apply Tags Filter (Task 4.4.3)
        if (selectedTags.length > 0) {
            result = result.filter((agent) => {
                const agentTags = Array.isArray(agent.tags) ? agent.tags : [];
                return selectedTags.every((tag) => agentTags.includes(tag));
            });
        }

        return result;
    }, [initialAgents, deferredSearch, selectedSkills, selectedCategory, selectedTags, requireSla, requireAuth]);

    const columns = useColumns();
    const gridParentRef = useRef<HTMLDivElement>(null);
    const [scrollMargin, setScrollMargin] = useState(0);

    const hasRows = filteredAgents.length > 0;
    useEffect(() => {
        const el = gridParentRef.current;
        if (!el) return;
        const update = () => setScrollMargin(el.offsetTop);
        update();
        const ro = new ResizeObserver(update);
        ro.observe(el);
        return () => ro.disconnect();
    }, [hasRows]);

    const rows = useMemo(
        () =>
            Array.from({ length: Math.ceil(filteredAgents.length / columns) }, (_, i) =>
                filteredAgents.slice(i * columns, (i + 1) * columns)
            ),
        [filteredAgents, columns]
    );

    const rowVirtualizer = useWindowVirtualizer({
        count: rows.length,
        estimateSize: () => 280,
        overscan: 3,
        scrollMargin,
        gap: 24,
    });

    return (
        <div className="flex flex-col md:flex-row gap-6">
            {/* Sidebar / Filters (Task 4.1.2, 4.1.3, 4.1.4) */}
            <div className="w-full md:w-64 shrink-0 space-y-6">
                <div className="rounded-lg border bg-card text-card-foreground shadow-sm p-4">
                    <h2 className="font-semibold mb-4">Search & Filters</h2>
                    <div className="space-y-4">
                        <div className="relative">
                            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                            <Input
                                type="search"
                                placeholder="Search agents..."
                                className="pl-8"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                            />
                        </div>

                        {/* Category Filter (Task 4.4.2) */}
                        <div className="pt-4 border-t">
                            <h3 className="text-sm font-medium mb-3">Category</h3>
                            <select
                                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                                value={selectedCategory}
                                onChange={(e) => setSelectedCategory(e.target.value)}
                            >
                                <option value="">All Categories</option>
                                {availableCategories.map((cat) => (
                                    <option key={cat} value={cat}>
                                        {cat}
                                    </option>
                                ))}
                            </select>
                        </div>

                        {/* Tags Filter (Task 4.4.3) */}
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

                        {/* Skill Filters (Task 4.1.3) */}
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

                        {/* Trust level filters (Task 4.1.4) */}
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

            {/* Main Content / Agent Cards Grid */}
            <div className="flex-1">
                {filteredAgents.length === 0 ? (
                    <div className="rounded-xl border border-dashed border-zinc-800 bg-zinc-950 p-12 flex flex-col items-center justify-center text-center relative overflow-hidden group">
                        <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:14px_24px] pointer-events-none" />
                        <div className="relative z-10 flex flex-col items-center max-w-md">
                            <div className="h-12 w-12 rounded-lg bg-zinc-900 border border-zinc-800 flex items-center justify-center mb-6">
                                <Search className="h-6 w-6 text-zinc-500" />
                            </div>
                            <h3 className="mb-3 text-xl font-medium tracking-tight text-white">No agents match your criteria</h3>
                            {searchQuery ? (
                                <p className="mb-6 text-sm text-zinc-400 leading-relaxed">
                                    We couldn&apos;t find any agents matching <code className="px-1.5 py-0.5 rounded-md bg-zinc-900 text-zinc-300 border border-zinc-800">{searchQuery}</code>. Try adjusting your filters or be the first to build and monetize this capability.
                                </p>
                            ) : (
                                <p className="mb-6 text-sm text-zinc-400 leading-relaxed">
                                    There are currently no agents that match your selected filters. Try broadening your search criteria.
                                </p>
                            )}
                            <Button asChild variant="outline" className="border-zinc-800 text-zinc-300 hover:bg-zinc-900 hover:text-white">
                                <Link href="/dashboard/register">Register an Agent</Link>
                            </Button>
                        </div>
                    </div>
                ) : (
                    <div ref={gridParentRef} className="flex-1">
                        <div
                            style={{
                                height: `${rowVirtualizer.getTotalSize()}px`,
                                width: '100%',
                                position: 'relative',
                            }}
                        >
                            {rowVirtualizer.getVirtualItems().map((virtualRow) => {
                                const rowAgents = rows[virtualRow.index] ?? [];
                                return (
                                    <div
                                        key={virtualRow.key}
                                        data-index={virtualRow.index}
                                        ref={rowVirtualizer.measureElement}
                                        style={{
                                            position: 'absolute',
                                            top: 0,
                                            left: 0,
                                            width: '100%',
                                            transform: `translateY(${virtualRow.start - rowVirtualizer.options.scrollMargin}px)`,
                                        }}
                                        className="pb-6"
                                    >
                                        <div
                                            className={cn(
                                                'grid gap-6',
                                                columns === 1 && 'grid-cols-1',
                                                columns === 2 && 'grid-cols-2',
                                                columns === 3 && 'grid-cols-3'
                                            )}
                                        >
                                            {rowAgents.map((agent) => (
                                                <Card key={agent.id ?? ''} className="flex flex-col transition-all hover:border-indigo-500/50 hover:shadow-md hover:-translate-y-1 duration-200">
                                                    <CardHeader>
                                                        <div className="flex items-start justify-between gap-4">
                                                            <CardTitle className="text-lg line-clamp-1">{agent.name}</CardTitle>
                                                            {agent.verification?.status === 'verified' && (
                                                                <div className="shrink-0 flex items-center justify-center rounded-full bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5" title="Protocol Verified">
                                                                    <ShieldCheck className="h-3.5 w-3.5 text-emerald-400 mr-1" />
                                                                    <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider">Verified</span>
                                                                </div>
                                                            )}
                                                        </div>
                                                        <CardDescription className="line-clamp-2 min-h-10 text-xs">
                                                            {agent.description}
                                                        </CardDescription>
                                                    </CardHeader>
                                                    <CardContent className="flex-1 space-y-4">
                                                        <div className="flex flex-wrap gap-2">
                                                            {(agent.capabilities?.skills as { id: string }[])?.slice(0, 3).map((skill) => (
                                                                <Badge key={skill.id} variant="secondary" className="text-xs">
                                                                    {skill.id}
                                                                </Badge>
                                                            )) || (
                                                                    <span className="text-xs italic text-muted-foreground">No specific skills listed</span>
                                                                )}
                                                            {Array.isArray(agent.capabilities?.skills) && agent.capabilities.skills.length > 3 && (
                                                                <Badge variant="outline" className="text-xs">+{agent.capabilities.skills.length - 3} more</Badge>
                                                            )}
                                                        </div>
                                                    </CardContent>
                                                    <CardFooter className="pt-4 border-t flex flex-col items-start gap-4">
                                                        <div className="flex items-center justify-between w-full">
                                                            <div className="flex flex-col gap-1">
                                                                <span className="text-xs font-mono text-zinc-500 truncate w-32" title={agent.id ?? ''}>
                                                                    {agent.id?.split(':').pop()}
                                                                </span>
                                                                <div className="flex gap-2 text-[10px] text-zinc-600 font-medium">
                                                                    <span>v{agent.capabilities?.asap_version || '2.0'}</span>
                                                                </div>
                                                            </div>
                                                            <Button asChild size="sm" variant="outline" className="shrink-0 border-zinc-800 text-zinc-300 hover:text-white hover:bg-zinc-800 transition-colors">
                                                                <Link href={`/agents/${encodeURIComponent(agent.id ?? '')}`}>View Details</Link>
                                                            </Button>
                                                        </div>
                                                    </CardFooter>
                                                </Card>
                                            ))}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
