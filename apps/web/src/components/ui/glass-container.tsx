import { cn } from "@/lib/utils";

interface GlassContainerProps {
  children: React.ReactNode;
  className?: string;
}

export function GlassContainer({ children, className }: GlassContainerProps) {
  return (
    <div
      className={cn(
        "overflow-hidden bg-gradient-to-b from-black/10 to-white/10 p-px rounded-2xl backdrop-blur-lg",
        "dark:from-white/10 dark:to-white/5"
      )}
    >
      <div
        className={cn(
          "bg-white/95 backdrop-blur-md rounded-2xl",
          "dark:bg-black/80",
          className
        )}
      >
        {children}
      </div>
    </div>
  );
}
