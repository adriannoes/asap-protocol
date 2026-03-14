import { Skeleton } from '@/components/ui/skeleton';
import { AgentCardSkeleton } from './agent-card-skeleton';

export default function BrowseLoading() {
  const skeletons = Array.from({ length: 9 }, (_, i) => <AgentCardSkeleton key={i} />);

  return (
    <div className="container mx-auto py-10 px-4 max-w-7xl">
      <div className="flex flex-col space-y-6">
        <div>
          <Skeleton className="h-9 w-64" />
          <Skeleton className="mt-2 h-5 w-96" />
        </div>

        <div className="flex flex-col md:flex-row gap-6">
          <div className="w-full md:w-64 shrink-0">
            <div className="rounded-lg border bg-card p-4 space-y-4">
              <Skeleton className="h-5 w-32" />
              <Skeleton className="h-10 w-full" />
              <div className="pt-4 border-t space-y-2">
                <Skeleton className="h-4 w-24" />
                <div className="flex flex-wrap gap-2">
                  {[1, 2, 3, 4].map((i) => (
                    <Skeleton key={i} className="h-6 w-16 rounded-full" />
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="flex-1">
            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
              {skeletons}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
