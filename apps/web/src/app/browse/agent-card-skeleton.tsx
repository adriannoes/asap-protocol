'use client';

/**
 * Skeleton that matches Agent Card dimensions exactly to prevent CLS (Task 4.2.2).
 * Must mirror the layout of the Card in browse-content.tsx.
 */

import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';

export function AgentCardSkeleton() {
  return (
    <Card className="flex flex-col transition-all">
      <CardHeader>
        <Skeleton className="h-5 w-3/4" data-slot="title" />
        <Skeleton className="mt-2 h-10 w-full" data-slot="description" />
      </CardHeader>
      <CardContent className="flex-1 space-y-4">
        <div className="flex flex-wrap gap-2">
          <Skeleton className="h-5 w-16 rounded-sm" />
          <Skeleton className="h-5 w-20 rounded-sm" />
          <Skeleton className="h-5 w-14 rounded-sm" />
        </div>
      </CardContent>
      <CardFooter className="pt-4 border-t flex justify-between">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-8 w-24 rounded-md" />
      </CardFooter>
    </Card>
  );
}
