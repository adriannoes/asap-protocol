import { cn } from "@/lib/utils";

/**
 * Ghost input/textarea styles for auth/register pages over WebGL Canvas.
 * Use as className override — do NOT modify global Input/Textarea.
 * @see design-system.md §8.6, sprint-M4-webgl-auth.md task 2.4
 */
export const ghostInputClassName = cn(
  "bg-transparent border-white/10 text-white placeholder:text-white/40",
  "focus:border-white/30 focus:ring-0 transition-colors",
  "text-base" // Prevents iOS Safari auto-zoom on focus (mobile-strategy.md §7)
);
