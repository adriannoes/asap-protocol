import { Metadata } from 'next';
import { HeroSection } from '@/components/landing/HeroSection';
import { WhatsNewRibbon } from '@/components/landing/WhatsNewRibbon';
import { FeaturedAgents } from '@/components/landing/FeaturedAgents';
import { FeaturesSection } from '@/components/landing/FeaturesSection';
import { HowItWorksSection } from '@/components/landing/HowItWorksSection';
import { fetchRegistry } from '@/lib/registry';

export const metadata: Metadata = {
  title: 'ASAP Protocol | Build for agents',
  description:
    'The next users of software are agents. ASAP provides discoverable capabilities, scoped identity, compliance checks, and SDKs that turn existing APIs into agent-ready interfaces.',
  openGraph: {
    title: 'ASAP Protocol | Build for agents',
    description:
      'The next users of software are agents. ASAP provides discoverable capabilities, scoped identity, compliance checks, and SDKs that turn existing APIs into agent-ready interfaces.',
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
