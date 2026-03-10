import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { DashboardClient } from '../dashboard-client';

vi.mock('next/navigation', () => ({
    useRouter: () => ({ refresh: vi.fn() }),
}));

vi.mock('../actions', () => ({
    fetchUserRegistrationIssues: vi.fn().mockResolvedValue({ success: true, data: [] }),
    revalidateUserRegistrationIssues: vi.fn().mockResolvedValue(undefined),
}));

vi.mock('@/auth', () => ({
    auth: vi.fn().mockResolvedValue({ user: { id: '1', username: 'test' }, accessToken: 'token' }),
}));

describe('DashboardClient', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders Agent Builder card with text and Open Agent Builder button', () => {
        render(<DashboardClient initialAgents={[]} username="test" />);
        expect(screen.getByText('Agent Builder')).toBeInTheDocument();
        expect(screen.getByRole('link', { name: /Open Agent Builder/i })).toBeInTheDocument();
    });

    it('Agent Builder button href includes ?from=asap', () => {
        render(<DashboardClient initialAgents={[]} username="test" />);
        const link = screen.getByRole('link', { name: /Open Agent Builder/i });
        expect(link).toHaveAttribute('href', expect.stringContaining('?from=asap'));
    });
});
