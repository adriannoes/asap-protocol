import { track } from '@vercel/analytics';

/** Flat property values accepted by Vercel Web Analytics `track()`. */
export type TrackPropertyValue = string | number | boolean | null | undefined;

export type TrackFn = (name: string, properties?: Record<string, TrackPropertyValue>) => void;

/**
 * Resolve a stable CTA id from a click target (supports nested children).
 *
 * @example
 * readCtaIdFromEventTarget(event.target) // 'hero-explore-agents' | null
 */
export function readCtaIdFromEventTarget(target: EventTarget | null): string | null {
  if (!(target instanceof Element)) {
    return null;
  }
  const host = target.closest('[data-cta]');
  if (!(host instanceof HTMLElement)) {
    return null;
  }
  const cta = host.dataset.cta?.trim();
  return cta ? cta : null;
}

/**
 * Emit a Vercel custom event for a CTA click.
 *
 * @example
 * emitCtaClick('docs-workflow-connectors', '/features/workflow-connectors');
 */
export function emitCtaClick(cta: string, path: string, trackFn: TrackFn = track): void {
  trackFn('cta_click', { cta, path });
}

/**
 * Primary button (`click`) and middle-button (`auxclick` button === 1) only.
 */
export function shouldTrackPointerEvent(event: MouseEvent): boolean {
  if (event.type === 'click') {
    return event.button === 0;
  }
  if (event.type === 'auxclick') {
    return event.button === 1;
  }
  return false;
}

/**
 * Document-delegated handler: find `[data-cta]` and emit `cta_click` when eligible.
 */
export function handleCtaPointerEvent(
  event: MouseEvent,
  path: string = typeof window !== 'undefined' ? window.location.pathname : '',
  trackFn: TrackFn = track
): void {
  if (!shouldTrackPointerEvent(event)) {
    return;
  }
  const cta = readCtaIdFromEventTarget(event.target);
  if (!cta) {
    return;
  }
  emitCtaClick(cta, path, trackFn);
}
