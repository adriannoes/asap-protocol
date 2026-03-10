import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Header } from '../Header';

vi.mock('@/auth', () => ({
    auth: vi.fn(),
    signIn: vi.fn(),
    signOut: vi.fn(),
}));

vi.mock('next/link', () => ({
    default: ({ children, href }: { children: React.ReactNode; href: string }) => (
        <a href={href}>{children}</a>
    ),
}));

vi.mock('../mobile-nav', () => ({
    MobileNav: ({ session }: { session: unknown }) => (
        <div data-testid="mobile-nav" data-session={session ? 'yes' : 'no'} />
    ),
}));

import * as authModule from '@/auth';
const auth = vi.mocked(authModule.auth);

describe('Header', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders Agent Builder link when session exists', async () => {
        auth.mockResolvedValue({
            user: { id: '1', name: 'Test User', email: 'test@example.com' },
        } as never);
        render(await Header());
        expect(screen.getByRole('link', { name: /Agent Builder/i })).toBeInTheDocument();
        const link = screen.getByRole('link', { name: /Agent Builder/i });
        expect(link).toHaveAttribute('href', expect.stringContaining('?from=asap'));
    });

    it('renders Build Agents CTA when session is null', async () => {
        auth.mockResolvedValue(null as never);
        render(await Header());
        const button = screen.getByRole('button', { name: /Build Agents/i });
        expect(button).toBeInTheDocument();
        expect(button.className).toContain('indigo');
    });

    it('does NOT render Agent Builder link when session is null', async () => {
        auth.mockResolvedValue(null as never);
        render(await Header());
        expect(screen.queryByRole('link', { name: /Agent Builder/i })).not.toBeInTheDocument();
    });

    it('does NOT render Build Agents CTA when session exists', async () => {
        auth.mockResolvedValue({
            user: { id: '1', name: 'Test User', email: 'test@example.com' },
        } as never);
        render(await Header());
        expect(screen.queryByRole('button', { name: /Build Agents/i })).not.toBeInTheDocument();
    });
});
