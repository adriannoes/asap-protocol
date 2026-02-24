import { MetadataRoute } from 'next';
import { fetchRegistry } from '../lib/registry';

export const revalidate = 60; // 1 minute (ISR cache)

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
    const baseUrl = process.env.NEXT_PUBLIC_APP_URL || 'https://asap-protocol.com';

    const agents = await fetchRegistry();

    // Exclude seeded/mock/loadtest agents so bots don't index fake pages.
    const validAgents = agents.filter(
        (a) =>
            a.id &&
            !a.id.includes('urn:asap:agent:mock:') &&
            !a.id.includes('urn:asap:agent:loadtest:') &&
            !a.id.includes('test') &&
            !a.id.includes('fixture')
    );

    const agentUrls = validAgents.map((agent) => ({
        url: `${baseUrl}/agents/${encodeURIComponent(agent.id as string)}`,
        lastModified: new Date(),
        changeFrequency: 'weekly' as const,
        priority: 0.8,
    }));

    return [
        {
            url: baseUrl,
            lastModified: new Date(),
            changeFrequency: 'daily',
            priority: 1,
        },
        {
            url: `${baseUrl}/browse`,
            lastModified: new Date(),
            changeFrequency: 'hourly',
            priority: 0.9,
        },
        {
            url: `${baseUrl}/dashboard`,
            lastModified: new Date(),
            changeFrequency: 'weekly',
            priority: 0.5,
        },
        ...agentUrls,
    ];
}
