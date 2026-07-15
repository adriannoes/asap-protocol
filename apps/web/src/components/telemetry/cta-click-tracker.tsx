'use client';

import { useEffect } from 'react';

import { handleCtaPointerEvent } from '@/lib/telemetry/track-cta-click';

/**
 * Global delegated listener for `[data-cta]` clicks (primary + middle).
 * Mount once in the root layout; keeps landing/feature pages as Server Components.
 *
 * @example
 * // apps/web/src/app/layout.tsx
 * <CtaClickTracker />
 */
export function CtaClickTracker(): null {
  useEffect(() => {
    const onPointer = (event: MouseEvent): void => {
      handleCtaPointerEvent(event);
    };
    document.addEventListener('click', onPointer);
    document.addEventListener('auxclick', onPointer);
    return () => {
      document.removeEventListener('click', onPointer);
      document.removeEventListener('auxclick', onPointer);
    };
  }, []);

  return null;
}
