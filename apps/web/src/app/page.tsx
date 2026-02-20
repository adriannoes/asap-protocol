import { Metadata } from 'next';
import { HeroSection } from '@/components/landing/HeroSection';
import { FeaturedAgents } from '@/components/landing/FeaturedAgents';
import { FeaturesSection } from '@/components/landing/FeaturesSection';
import { HowItWorksSection } from '@/components/landing/HowItWorksSection';

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

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col bg-zinc-950 font-sans">
      <HeroSection />
      <FeaturedAgents />
      <FeaturesSection />
      <HowItWorksSection />
    </main>
  );
}
