import Link from 'next/link';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { RegistryAgent } from '@/types/registry';

interface AgentCardProps {
    agent: RegistryAgent;
}

export function AgentCard({ agent }: AgentCardProps) {
    return (
        <Link href={`/agents/${encodeURIComponent(agent.id || '')}`} className="block h-full outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 rounded-xl">
            <Card className="h-full border-zinc-800 bg-zinc-950/50 backdrop-blur-sm transition-all duration-300 hover:-translate-y-1 hover:border-indigo-500/40 hover:bg-zinc-900/80 hover:shadow-[0_8px_30px_rgb(0,0,0,0.12)] group">
                <CardHeader>
                    <div className="flex justify-between items-start gap-4 mb-2">
                        <CardTitle className="line-clamp-1 text-xl text-zinc-100 group-hover:text-indigo-400 transition-colors">
                            {agent.name}
                        </CardTitle>
                        {agent.version && (
                            <Badge variant="outline" className="shrink-0 font-mono bg-black/20 border-zinc-800 text-zinc-400">
                                {agent.version}
                            </Badge>
                        )}
                    </div>
                    <CardDescription className="line-clamp-3 text-sm text-zinc-400 leading-relaxed min-h-[60px]">
                        {agent.description || "No description provided."}
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="flex flex-wrap gap-2 mt-auto">
                        {agent.capabilities?.skills?.slice(0, 4).map((skill: { id: string }, i: number) => (
                            <Badge
                                key={i}
                                variant="outline"
                                className="border-zinc-800/80 bg-zinc-900/50 text-xs text-zinc-300 font-medium group-hover:border-zinc-700 transition-colors"
                            >
                                {skill.id}
                            </Badge>
                        ))}
                        {agent.capabilities?.skills && agent.capabilities.skills.length > 4 && (
                            <Badge
                                variant="outline"
                                className="border-zinc-800/60 bg-transparent text-xs text-zinc-500 font-medium"
                            >
                                +{agent.capabilities.skills.length - 4}
                            </Badge>
                        )}
                    </div>
                </CardContent>
            </Card>
        </Link>
    );
}
