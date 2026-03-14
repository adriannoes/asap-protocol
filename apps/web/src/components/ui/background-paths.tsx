"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { useIsMobile } from "@/hooks/use-mobile";

const DEFAULT_PATH_COUNT_DESKTOP = 6;
const DEFAULT_PATH_COUNT_MOBILE = 4;
const BASE_ANIMATION_DURATION = 20;
const DURATION_INCREMENT = 5;
const BASE_OPACITY = 0.05;
const OPACITY_INCREMENT = 0.02;

interface BackgroundPathsProps {
  className?: string;
  pathCount?: number;
}

function generatePathData(index: number, total: number): string {
  const spread = 200;
  const yOffset = (index - total / 2) * (spread / total);

  return [
    `M -100 ${300 + yOffset}`,
    `C 200 ${100 + yOffset * 0.8}, 400 ${500 + yOffset * 1.2}, 600 ${250 + yOffset}`,
    `S 900 ${400 + yOffset * 0.6}, 1100 ${300 + yOffset}`,
  ].join(" ");
}

export function BackgroundPaths({ className, pathCount }: BackgroundPathsProps) {
  const isMobile = useIsMobile();
  const count = pathCount ?? (isMobile ? DEFAULT_PATH_COUNT_MOBILE : DEFAULT_PATH_COUNT_DESKTOP);

  return (
    <div
      className={cn("absolute inset-0 overflow-hidden -z-10", className)}
      data-testid="background-paths"
    >
      <svg
        className="h-full w-full text-foreground"
        viewBox="0 0 1000 600"
        preserveAspectRatio="xMidYMid slice"
        fill="none"
      >
        {Array.from({ length: count }, (_, i) => (
          <motion.path
            key={i}
            d={generatePathData(i, count)}
            stroke="currentColor"
            strokeWidth={0.5}
            opacity={BASE_OPACITY + i * OPACITY_INCREMENT}
            strokeDasharray="1000"
            initial={{ strokeDashoffset: 1000 }}
            animate={{ strokeDashoffset: 0 }}
            transition={{
              duration: BASE_ANIMATION_DURATION + i * DURATION_INCREMENT,
              repeat: Infinity,
              repeatType: "loop",
              ease: "linear",
            }}
          />
        ))}
      </svg>
    </div>
  );
}
