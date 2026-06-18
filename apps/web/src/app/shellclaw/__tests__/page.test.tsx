import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ShellClawPage from '../page';

vi.mock('@/components/ui/background-paths', () => ({
    BackgroundPaths: () => null,
}));

describe('ShellClawPage', () => {
    it('renders hero and primary CTAs', () => {
        render(<ShellClawPage />);

        expect(screen.getByRole('heading', { level: 1, name: 'ShellClaw' })).toBeInTheDocument();
        expect(screen.getByText(/first physical AI agent/i)).toBeInTheDocument();

        const githubLink = screen.getByRole('link', { name: /view on github/i });
        expect(githubLink).toHaveAttribute('href', 'https://github.com/adriannoes/shellclaw');
        expect(githubLink).toHaveAttribute('target', '_blank');
        expect(githubLink).toHaveAttribute('rel', 'noopener noreferrer');

        expect(screen.getByRole('link', { name: /registry guide/i })).toHaveAttribute(
            'href',
            '/docs/register',
        );
        expect(screen.getByRole('link', { name: /browse marketplace/i })).toHaveAttribute(
            'href',
            '/browse',
        );
    });
});
