import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { BrowseContent } from '../browse-content';
import { Manifest } from '@/types/protocol';

// Mock test data
const mockAgents: Manifest[] = [
    {
        id: 'urn:asap:agent:user1:search-bot',
        name: 'Search Bot',
        description: 'A bot that searches the web',
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        version: '1.0.0' as any,
        endpoints: { asap: 'https://api.example.com/search' },
        capabilities: {
            asap_version: '0.1',
            skills: [
                { id: 'search', description: 'Web search' },
                { id: 'analysis', description: 'Data analysis' }
            ]
        }
    },
    {
        id: 'urn:asap:agent:user2:secure-writer',
        name: 'Secure Writer',
        description: 'Writes secure code',
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        version: '1.0.0' as any,
        endpoints: { asap: 'https://api.example.com/write' },
        sla: {
            availability: '99.9%',
            max_latency_p95_ms: 200,
            max_error_rate: '0.1%',
            support_hours: '24/7'
        },
        auth: { schemes: ['Bearer'] },
        capabilities: {
            asap_version: '0.1',
            skills: [
                { id: 'coding', description: 'Writes code' },
                { id: 'analysis', description: 'Code analysis' }
            ]
        }
    }
];

describe('BrowseContent', () => {
    it('renders all agents initially', () => {
        render(<BrowseContent initialAgents={mockAgents} />);
        expect(screen.getByText('Search Bot')).toBeInTheDocument();
        expect(screen.getByText('Secure Writer')).toBeInTheDocument();
    });

    it('filters agents by text search (debounced)', async () => {
        render(<BrowseContent initialAgents={mockAgents} />);

        const searchInput = screen.getByPlaceholderText('Search agents...');
        fireEvent.change(searchInput, { target: { value: 'secure' } });

        // Wait for debounce (300ms)
        await waitFor(() => {
            expect(screen.queryByText('Search Bot')).not.toBeInTheDocument();
            expect(screen.getByText('Secure Writer')).toBeInTheDocument();
        }, { timeout: 1000 });
    });

    it('filters agents by skill selection', () => {
        render(<BrowseContent initialAgents={mockAgents} />);

        // Initial state - both visible
        expect(screen.getByText('Search Bot')).toBeInTheDocument();
        expect(screen.getByText('Secure Writer')).toBeInTheDocument();

        // Click the 'coding' skill badge
        const codingBadge = screen.getAllByText('coding')[0];
        fireEvent.click(codingBadge);

        // Only Secure Writer should have 'coding'
        expect(screen.queryByText('Search Bot')).not.toBeInTheDocument();
        expect(screen.getByText('Secure Writer')).toBeInTheDocument();
    });

    it('filters agents by SLA requirement', () => {
        render(<BrowseContent initialAgents={mockAgents} />);

        const slaCheckbox = screen.getByLabelText(/Has published SLA/i);
        fireEvent.click(slaCheckbox);

        // Secure Writer has an SLA, Search Bot doesn't
        expect(screen.queryByText('Search Bot')).not.toBeInTheDocument();
        expect(screen.getByText('Secure Writer')).toBeInTheDocument();
    });

    it('filters agents by Authentication requirement', () => {
        render(<BrowseContent initialAgents={mockAgents} />);

        const authCheckbox = screen.getByLabelText(/Requires Authentication/i);
        fireEvent.click(authCheckbox);

        // Secure Writer requires "Bearer" Auth, Search Bot has no Auth
        expect(screen.queryByText('Search Bot')).not.toBeInTheDocument();
        expect(screen.getByText('Secure Writer')).toBeInTheDocument();
    });

    it('shows "No agents found" when filters yield no results', async () => {
        render(<BrowseContent initialAgents={mockAgents} />);

        const searchInput = screen.getByPlaceholderText('Search agents...');
        fireEvent.change(searchInput, { target: { value: 'nonexistent-agent-name' } });

        await waitFor(() => {
            expect(screen.queryByText('Search Bot')).not.toBeInTheDocument();
            expect(screen.queryByText('Secure Writer')).not.toBeInTheDocument();
            expect(screen.getByText('No agents found')).toBeInTheDocument();
            expect(screen.getByText('Try adjusting your search criteria.')).toBeInTheDocument();
        }, { timeout: 1000 });
    });
});
