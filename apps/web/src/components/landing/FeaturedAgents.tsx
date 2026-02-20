'use client';

import { useEffect, useState } from 'react';
import { Manifest } from '@/types/protocol';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Carousel,
  CarouselContent,
  CarouselItem,
  CarouselNext,
  CarouselPrevious,
} from '@/components/ui/carousel';
import { Badge } from '@/components/ui/badge';
import { fetchRegistry } from '@/lib/registry';

export function FeaturedAgents() {
  const [agents, setAgents] = useState<Manifest[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadAgents() {
      try {
        const data = await fetchRegistry();
        // Just mock picking a few agents for the carousel for now
        setAgents(data.slice(0, 6));
      } catch (err) {
        console.error('Failed to fetch featured agents', err);
      } finally {
        setIsLoading(false);
      }
    }
    loadAgents();
  }, []);

  if (isLoading) {
    return (
      <section className="w-full border-t border-zinc-900 bg-zinc-950 py-12 md:py-24">
        <div className="container mx-auto px-4 md:px-6">
          <div className="flex h-48 items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent" />
          </div>
        </div>
      </section>
    );
  }

  if (agents.length === 0) {
    return null; // Don't show the section if no agents yet
  }

  return (
    <section className="w-full overflow-hidden border-t border-zinc-900 bg-zinc-950 py-20 text-center lg:text-left">
      <div className="container mx-auto px-4 md:px-6">
        <div className="mb-10 flex flex-col gap-4 text-center">
          <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
            Featured Agents
          </h2>
          <p className="mx-auto max-w-[600px] text-zinc-400">
            Top-rated and highly trusted autonomous agents ready to integrate into your stack.
          </p>
        </div>

        <div className="mx-auto max-w-5xl px-8">
          {/* We add px-8 to Carousel wrapper so arrows have space without overlapping cards */}
          <Carousel
            opts={{
              align: 'start',
              loop: true,
            }}
            className="w-full"
          >
            <CarouselContent className="-ml-2 md:-ml-4">
              {agents.map((agent) => (
                <CarouselItem
                  key={agent.id}
                  className="basis-full pl-2 md:basis-1/2 md:pl-4 lg:basis-1/3"
                >
                  <div className="p-1">
                    <Card className="border-zinc-800 bg-zinc-950/50 backdrop-blur-sm transition-all hover:border-indigo-500/50 hover:bg-zinc-900/80 hover:shadow-lg hover:shadow-indigo-500/10">
                      <CardHeader className="pb-4">
                        <div className="mb-2 flex items-start justify-between">
                          <CardTitle className="line-clamp-1 text-xl text-white">
                            {agent.name}
                          </CardTitle>
                          {/* Trust level will be computed externally in v2.0 Lite Registry via verified maintainers. Hiding badge for now. */}
                        </div>
                        <CardDescription className="line-clamp-2 min-h-[40px] text-zinc-400">
                          {agent.description}
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {agent.capabilities?.skills?.slice(0, 3).map((skill, i) => (
                            <Badge
                              key={i}
                              variant="outline"
                              className="border-zinc-700 text-xs text-zinc-300"
                            >
                              {skill.id}
                            </Badge>
                          ))}
                          {agent.capabilities?.skills && agent.capabilities.skills.length > 3 && (
                            <Badge
                              variant="outline"
                              className="border-zinc-700 text-xs text-zinc-500"
                            >
                              +{agent.capabilities.skills.length - 3}
                            </Badge>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                </CarouselItem>
              ))}
            </CarouselContent>
            <CarouselPrevious className="border-zinc-800 bg-zinc-950 text-white hover:bg-zinc-800 hover:text-white" />
            <CarouselNext className="border-zinc-800 bg-zinc-950 text-white hover:bg-zinc-800 hover:text-white" />
          </Carousel>
        </div>
      </div>
    </section>
  );
}
