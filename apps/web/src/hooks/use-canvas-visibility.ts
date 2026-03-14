"use client";

import { type RefObject, useEffect, useState } from "react";

/**
 * Tracks whether an element is visible in the viewport via IntersectionObserver.
 * Used to pause Canvas rendering when off-screen (PRD §7 performance).
 */
export function useCanvasVisibility(ref: RefObject<HTMLElement | null>): boolean {
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => setIsVisible(entry?.isIntersecting ?? true),
      { threshold: 0.1 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [ref]);

  return isVisible;
}
