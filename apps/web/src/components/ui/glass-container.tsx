import { cn } from "@/lib/utils";

interface GlassContainerProps {
  children: React.ReactNode;
  className?: string;
}

export function GlassContainer({ children, className }: GlassContainerProps) {
  return (
    <div
      className={cn(
        // Outer wrapper: 1px gradient pseudo-border
        "overflow-hidden bg-gradient-to-b from-black/10 to-white/10 p-px rounded-2xl backdrop-blur-lg",
        // Dark mode equivalent
        "dark:from-white/10 dark:to-white/5"
      )}
    >
      <div
        className={cn(
          // Inner element: frosted glass
          // Use rounded-2xl (Tailwind token) instead of arbitrary rounded-[calc(...)]
          // The 1px difference from p-px is visually negligible
          "bg-white/95 backdrop-blur-md rounded-2xl",
          // Dark mode
          "dark:bg-black/80",
          className
        )}
      >
        {children}
      </div>
    </div>
  );
}
