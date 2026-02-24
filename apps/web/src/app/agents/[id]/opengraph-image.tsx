import { ImageResponse } from 'next/og';
import { fetchAgentById } from '../../../lib/registry';

export const runtime = 'edge';

// Image metadata
export const alt = 'ASAP Protocol Agent';
export const size = {
    width: 1200,
    height: 630,
};

export const contentType = 'image/png';

export default async function Image({ params }: { params: { id: string } }) {
    const agentId = decodeURIComponent(params.id);
    const agent = await fetchAgentById(agentId);

    if (!agent) {
        return new ImageResponse(
            (
                <div
                    style={{
                        fontSize: 48,
                        background: 'linear-gradient(to right, #09090b, #18181b)',
                        color: '#a1a1aa',
                        width: '100%',
                        height: '100%',
                        display: 'flex',
                        textAlign: 'center',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontFamily: 'sans-serif',
                    }}
                >
                    Agent Not Found | ASAP Protocol
                </div>
            ),
            { ...size }
        );
    }

    return new ImageResponse(
        (
            <div
                style={{
                    background: 'linear-gradient(to bottom right, #09090b 0%, #18181b 100%)',
                    width: '100%',
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'flex-start',
                    justifyContent: 'center',
                    padding: '80px',
                    fontFamily: 'sans-serif',
                    color: 'white',
                }}
            >
                <div
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        marginBottom: '40px',
                    }}
                >
                    {/* Mock Logo / Protocol Name */}
                    <div
                        style={{
                            fontSize: 32,
                            fontWeight: 800,
                            background: 'linear-gradient(to right, #38bdf8, #818cf8)',
                            backgroundClip: 'text',
                            color: 'transparent',
                            letterSpacing: '-0.05em',
                        }}
                    >
                        ASAP Protocol
                    </div>
                    <div style={{ marginLeft: '16px', fontSize: 24, color: '#52525b' }}>/</div>
                    <div style={{ marginLeft: '16px', fontSize: 24, color: '#a1a1aa' }}>Agent Details</div>
                </div>

                <div
                    style={{
                        fontSize: 72,
                        fontWeight: 800,
                        lineHeight: 1.1,
                        letterSpacing: '-0.02em',
                        marginBottom: '24px',
                        display: 'flex',
                        alignItems: 'center',
                    }}
                >
                    {agent.name}
                    {agent.verification?.status === 'verified' && (
                        <div
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                marginLeft: '24px',
                                background: 'rgba(34, 197, 94, 0.1)',
                                border: '2px solid rgba(34, 197, 94, 0.5)',
                                color: '#22c55e',
                                borderRadius: '9999px',
                                padding: '4px 16px',
                                fontSize: 24,
                                fontWeight: 600,
                            }}
                        >
                            Verified
                        </div>
                    )}
                </div>

                <div
                    style={{
                        fontSize: 32,
                        color: '#a1a1aa',
                        lineHeight: 1.4,
                        marginBottom: '40px',
                        maxWidth: '900px',
                        display: '-webkit-box',
                        WebkitLineClamp: 3,
                        WebkitBoxOrient: 'vertical',
                        overflow: 'hidden',
                    }}
                >
                    {agent.description}
                </div>

                <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                    {agent.capabilities?.skills?.slice(0, 4).map((skill) => (
                        <div
                            key={skill.id}
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                background: '#27272a',
                                color: '#d4d4d8',
                                padding: '8px 24px',
                                borderRadius: '8px',
                                fontSize: 24,
                                fontWeight: 500,
                            }}
                        >
                            {skill.id}
                        </div>
                    ))}
                    {(agent.capabilities?.skills?.length ?? 0) > 4 && (
                        <div
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                background: '#18181b',
                                color: '#71717a',
                                padding: '8px 24px',
                                borderRadius: '8px',
                                fontSize: 24,
                                border: '1px solid #27272a',
                            }}
                        >
                            +{(agent.capabilities?.skills?.length ?? 0) - 4} more
                        </div>
                    )}
                </div>

                <div
                    style={{
                        position: 'absolute',
                        bottom: '80px',
                        left: '80px',
                        display: 'flex',
                        fontSize: 24,
                        color: '#52525b',
                        fontFamily: 'monospace',
                    }}
                >
                    {agent.id}
                </div>
            </div>
        ),
        {
            ...size,
        }
    );
}
