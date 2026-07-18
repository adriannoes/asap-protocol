import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { BUILD_FOR_AGENTS_GUIDE_URL, STARTERS_URL } from '@/lib/landing/dist-loop-links';
import { EXTERNAL_LINK_FOCUS_CLASS, OpensInNewTabHint } from '@/components/links/opens-in-new-tab';
import { cn } from '@/lib/utils';

const PRIMARY_BUTTON_CLASS = 'w-full bg-white text-black hover:bg-zinc-200 min-[400px]:w-auto';
const OUTLINE_BUTTON_CLASS =
  'w-full border-zinc-800 text-zinc-300 hover:bg-zinc-900 hover:text-white min-[400px]:w-auto';

export type DistLoopPrimaryCtasProps = {
  /** Stable `data-cta` for the Build for agents guide link. */
  buildForAgentsCtaId: string;
  /** Stable `data-cta` for the starters tree link. */
  viewStartersCtaId: string;
  /**
   * How It Works uses outline for the secondary starters CTA; Hero keeps both primary.
   * Provenance: thermo-nuclear Nice-to-Have — shared Dist Loop CTA markup.
   */
  startersVariant?: 'default' | 'outline';
  className?: string;
};

/**
 * Shared Dist Loop primary CTAs (guide + starters) for homepage sections.
 *
 * @example
 * ```tsx
 * <DistLoopPrimaryCtas
 *   buildForAgentsCtaId={HOMEPAGE_HERO_CTA_IDS.buildForAgents}
 *   viewStartersCtaId={HOMEPAGE_HERO_CTA_IDS.viewStarters}
 * />
 * ```
 */
export function DistLoopPrimaryCtas({
  buildForAgentsCtaId,
  viewStartersCtaId,
  startersVariant = 'default',
  className,
}: DistLoopPrimaryCtasProps) {
  const startersIsOutline = startersVariant === 'outline';

  return (
    <div
      className={cn(
        'flex flex-col justify-center gap-4 min-[400px]:flex-row min-[400px]:flex-wrap',
        className
      )}
    >
      <Button asChild size="lg" className={PRIMARY_BUTTON_CLASS}>
        <Link
          href={BUILD_FOR_AGENTS_GUIDE_URL}
          target="_blank"
          rel="noopener noreferrer"
          data-cta={buildForAgentsCtaId}
          className={EXTERNAL_LINK_FOCUS_CLASS}
        >
          Build for agents
          <OpensInNewTabHint />
        </Link>
      </Button>
      <Button
        asChild
        size="lg"
        variant={startersIsOutline ? 'outline' : 'default'}
        className={startersIsOutline ? OUTLINE_BUTTON_CLASS : PRIMARY_BUTTON_CLASS}
      >
        <Link
          href={STARTERS_URL}
          target="_blank"
          rel="noopener noreferrer"
          data-cta={viewStartersCtaId}
          className={EXTERNAL_LINK_FOCUS_CLASS}
        >
          View starters
          <OpensInNewTabHint />
        </Link>
      </Button>
    </div>
  );
}
