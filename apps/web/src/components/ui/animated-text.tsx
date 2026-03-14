"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

const STAGGER_INTERVAL = 0.05;
const SPRING_STIFFNESS = 150;
const SPRING_DAMPING = 25;
const INITIAL_Y_OFFSET = 20;

interface AnimatedTextProps {
  text: string;
  className?: string;
  as?: "h1" | "h2" | "h3" | "p" | "span";
  delay?: number;
}

export function AnimatedText({
  text,
  className,
  as: Tag = "h1",
  delay = 0,
}: AnimatedTextProps) {
  const words = text.split(" ");

  return (
    <Tag className={cn(className)}>
      <span className="sr-only">{text}</span>
      <span aria-hidden="true">
        {words.map((word, i) => (
          <motion.span
            key={i}
            className="inline-block mr-[0.25em]"
            initial={{ y: INITIAL_Y_OFFSET, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{
              type: "spring",
              stiffness: SPRING_STIFFNESS,
              damping: SPRING_DAMPING,
              delay: delay + i * STAGGER_INTERVAL,
            }}
          >
            {word}
          </motion.span>
        ))}
      </span>
    </Tag>
  );
}
