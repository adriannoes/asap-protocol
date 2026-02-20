'use client';

import { useState, useMemo, useEffect } from 'react';
import { Manifest } from '@/types/protocol';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Search } from 'lucide-react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface BrowseContentProps {
    initialAgents: Manifest[];
}

export function BrowseContent({ initialAgents }: BrowseContentProps) {
    const [searchQuery, setSearchQuery] = useState('');
    const [debouncedSearch, setDebouncedSearch] = useState('');
    const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
    const [requireSla, setRequireSla] = useState(false);
    const [requireAuth, setRequireAuth] = useState(false);

    // Debounce search query (Task 4.1.2)
    useEffect(() => {
        const timer = setTimeout(() => {
            setDebouncedSearch(searchQuery);
        }, 300);
        return () => clearTimeout(timer);
    }, [searchQuery]);

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

    // Filter agents based on search, selected skills, and trust levels
    const filteredAgents = useMemo(() => {
        let result = initialAgents;

        // Apply Search Filter
        if (debouncedSearch) {
            const lowerQuery = debouncedSearch.toLowerCase();
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

        return result;
    }, [initialAgents, debouncedSearch, selectedSkills, requireSla, requireAuth]);

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
                    <div className="rounded-lg border border-dashed p-10 flex flex-col items-center justify-center text-muted-foreground text-center">
                        <p className="text-lg font-medium">No agents found</p>
                        <p className="text-sm">Try adjusting your search criteria.</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
                        {filteredAgents.map((agent) => (
                            <Card key={agent.id ?? ''} className="flex flex-col transition-all hover:border-indigo-500/50 hover:shadow-md hover:-translate-y-1 duration-200">
                                <CardHeader>
                                    <CardTitle className="text-lg line-clamp-1">{agent.name}</CardTitle>
                                    <CardDescription className="line-clamp-2 min-h-10 text-xs">
                                        {agent.description}
                                    </CardDescription>
                                </CardHeader>
                                <CardContent className="flex-1 space-y-4">
                                    <div className="flex flex-wrap gap-2">
                                        {/* Safe mapping for skills array which might be under capabilities */}
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
                                <CardFooter className="pt-4 border-t flex justify-between">
                                    <span className="text-xs text-muted-foreground truncate w-24" title={agent.id ?? ''}>
                                        {agent.id?.split(':').pop()}
                                    </span>
                                    <Button asChild size="sm" variant="outline">
                                        <Link href={`/agents/${encodeURIComponent(agent.id ?? '')}`}>View Details</Link>
                                    </Button>
                                </CardFooter>
                            </Card>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
