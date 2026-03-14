import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface BentoGridProps {
    children: React.ReactNode;
    className?: string;
}

export function BentoGrid({ children, className }: BentoGridProps) {
    return (
        <div
            className={cn(
                'grid grid-cols-1 md:grid-cols-3 gap-3',
                className
            )}
        >
            {children}
        </div>
    );
}

function slugify(title: string): string {
    return title
        .toLowerCase()
        .replace(/\s+/g, '-')
        .replace(/[^a-z0-9-]/g, '');
}

interface BentoCardProps {
    title: string;
    description: string;
    icon: LucideIcon;
    value?: string | number;
    className?: string;
}

export function BentoCard({
    title,
    description,
    icon: Icon,
    value,
    className,
}: BentoCardProps) {
    const titleSlug = slugify(title);

    return (
        <div
            data-testid={`bento-card-${titleSlug}`}
            className={cn(
                'border border-border bg-card rounded-xl p-6 relative overflow-hidden group transition-all duration-300',
                'will-change-transform',
                'active:scale-[0.98] sm:active:scale-100',
                '[@media(hover:hover)]:hover:-translate-y-0.5 [@media(hover:hover)]:hover:shadow-sm',
                className
            )}
        >
            {/* Radial grid reveal on hover (scoped to pointer devices per mobile-strategy §4) */}
            <div
                className="absolute inset-0 opacity-0 [@media(hover:hover)]:group-hover:opacity-100 transition-opacity duration-500 pointer-events-none"
                style={{
                    backgroundImage:
                        'radial-gradient(circle, rgba(0,0,0,0.02) 1px, transparent 1px)',
                    backgroundSize: '4px 4px',
                }}
                aria-hidden
            />
            {/* Gleam border overlay (scoped to pointer devices per mobile-strategy §4) */}
            <div
                className="absolute inset-0 opacity-0 [@media(hover:hover)]:group-hover:opacity-100 transition-opacity duration-500 pointer-events-none bg-gradient-to-br from-transparent via-muted to-transparent rounded-xl"
                aria-hidden
            />
            <div className="relative z-10">
                <div className="bg-muted rounded-lg p-2 mb-3 w-fit">
                    <Icon className="h-5 w-5 text-muted-foreground" />
                </div>
                {value !== undefined && (
                    <p className="text-3xl font-bold font-mono tracking-tight mb-1">
                        {value}
                    </p>
                )}
                <h3 className="font-semibold text-sm">{title}</h3>
                <p className="text-xs text-muted-foreground mt-0.5">{description}</p>
            </div>
        </div>
    );
}
