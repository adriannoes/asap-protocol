import { Metadata } from 'next';
import { HeroSection } from '@/components/landing/HeroSection';
import { WhatsNewRibbon } from '@/components/landing/WhatsNewRibbon';
import { FeaturedAgents } from '@/components/landing/FeaturedAgents';
import { FeaturesSection } from '@/components/landing/FeaturesSection';
import { HowItWorksSection } from '@/components/landing/HowItWorksSection';
import { fetchRegistry } from '@/lib/registry';

export const metadata: Metadata = {
  title: 'ASAP Protocol | The Marketplace for Autonomous Agents',
  description:
    'Discover, verify, and integrate specialized AI agents into your workflows using the open ASAP Protocol standard.',
  openGraph: {
    title: 'ASAP Protocol | The Marketplace for Autonomous Agents',
    description:
      'Discover, verify, and integrate specialized AI agents into your workflows using the open ASAP Protocol standard.',
    type: 'website',
  },
};

export default async function Home() {
  const allAgents = await fetchRegistry();
  const featuredAgents = allAgents.slice(0, 6);

  return (
    <main className="flex min-h-screen flex-col bg-zinc-950 font-sans">
      <HeroSection />
      <WhatsNewRibbon />
      <FeaturedAgents agents={featuredAgents} />
      <FeaturesSection />
      <HowItWorksSection />
    </main>
  );
}
