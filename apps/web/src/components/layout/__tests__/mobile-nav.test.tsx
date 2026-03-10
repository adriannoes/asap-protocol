import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MobileNav } from '../mobile-nav';

vi.mock('next/link', () => ({
    default: ({ children, href }: { children: React.ReactNode; href: string }) => (
        <a href={href}>{children}</a>
    ),
}));

const mockSessionWithUser = {
    user: { id: '1', name: 'Test User', email: 'test@example.com' },
    expires: '2025-12-31',
};

function openMobileNav() {
    fireEvent.click(screen.getByRole('button', { name: /Toggle Menu/i }));
}

describe('MobileNav', () => {
    it('renders Agent Builder link when session.user exists', () => {
        render(<MobileNav session={mockSessionWithUser as never} />);
        openMobileNav();
        const link = screen.getByRole('link', { name: /Agent Builder/i });
        expect(link).toBeInTheDocument();
        expect(link).toHaveAttribute('href', expect.stringContaining('?from=asap'));
    });

    it('renders Build Agents CTA when session is null', () => {
        render(<MobileNav session={null} />);
        openMobileNav();
        const link = screen.getByRole('link', { name: /Build Agents/i });
        expect(link).toBeInTheDocument();
        expect(link).toHaveAttribute('href', expect.stringContaining('/api/auth/signin'));
        expect(link.className).toContain('indigo');
    });
});
