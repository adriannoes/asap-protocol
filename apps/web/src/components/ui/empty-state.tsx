import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  actionLabel?: string;
  actionHref?: string;
  className?: string;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  actionLabel,
  actionHref,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center py-16 text-center space-y-4",
        className
      )}
      data-testid="empty-state"
    >
      <Icon
        className="h-12 w-12 text-muted-foreground opacity-50 shrink-0"
        aria-hidden
      />
      <div className="max-w-sm space-y-2">
        <h2 className="text-lg font-semibold text-foreground">{title}</h2>
        <p className="text-sm text-muted-foreground text-center">
          {description}
        </p>
      </div>
      {actionLabel && actionHref && (
        <Button asChild data-testid="empty-state-action">
          <Link href={actionHref}>{actionLabel}</Link>
        </Button>
      )}
    </div>
  );
}
