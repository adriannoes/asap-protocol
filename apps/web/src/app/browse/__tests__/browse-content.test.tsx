import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { BrowseContent } from '../browse-content';
import type { RegistryAgent } from '@/types/registry';

const mockSearchParams = new URLSearchParams();
vi.mock('next/navigation', () => ({
    useRouter: () => ({ replace: vi.fn(), push: vi.fn(), refresh: vi.fn() }),
    usePathname: () => '/browse',
    useSearchParams: () => mockSearchParams,
}));

// Mock test data
const mockAgents: RegistryAgent[] = [
    {
        id: 'urn:asap:agent:user1:search-bot',
        name: 'Search Bot',
        description: 'A bot that searches the web',
        version: 1,
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
        version: 1,
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
    },
    {
        id: 'urn:asap:agent:edge:jetson-demo',
        name: 'Jetson Edge Demo',
        description: 'Edge accelerator with GPIO',
        version: 1,
        endpoints: { asap: 'https://api.example.com/edge' },
        hardware_class: 'edge_accelerator',
        inference_modes: ['cloud', 'local_cuda'],
        hardware_io: ['gpio', 'i2c'],
        capabilities: {
            asap_version: '2.1',
            skills: [{ id: 'gpio_control', description: 'GPIO control' }],
        },
    },
    {
        id: 'urn:asap:agent:edge:rpi-demo',
        name: 'RPi Edge Demo',
        description: 'SBC with local CPU inference',
        version: 1,
        endpoints: { asap: 'https://api.example.com/rpi' },
        hardware_class: 'sbc',
        inference_modes: ['cloud', 'local_cpu'],
        hardware_io: ['gpio'],
        capabilities: {
            asap_version: '2.1',
            skills: [{ id: 'assistant', description: 'Assistant' }],
        },
    },
];

describe('BrowseContent', () => {
    it('renders all agents initially', () => {
        render(<BrowseContent initialAgents={mockAgents} />);
        expect(screen.getByText('Search Bot')).toBeInTheDocument();
        expect(screen.getByText('Secure Writer')).toBeInTheDocument();
    });

    it('filters agents by text search (debounced)', async () => {
        render(<BrowseContent initialAgents={mockAgents} />);

        const searchInput = screen.getByPlaceholderText('Search agents by name or description...');
        fireEvent.change(searchInput, { target: { value: 'secure' } });

        await waitFor(() => {
            expect(screen.queryByText('Search Bot')).not.toBeInTheDocument();
            expect(screen.getByText('Secure Writer')).toBeInTheDocument();
        }, { timeout: 1000 });
    });

    it('filters agents by skill selection', () => {
        render(<BrowseContent initialAgents={mockAgents} />);

        expect(screen.getByText('Search Bot')).toBeInTheDocument();
        expect(screen.getByText('Secure Writer')).toBeInTheDocument();

        const codingBadge = screen.getAllByText('coding')[0];
        fireEvent.click(codingBadge);

        expect(screen.queryByText('Search Bot')).not.toBeInTheDocument();
        expect(screen.getByText('Secure Writer')).toBeInTheDocument();
    });

    it('filters agents by SLA requirement', () => {
        render(<BrowseContent initialAgents={mockAgents} />);

        const slaCheckbox = screen.getByLabelText(/Has published SLA/i);
        fireEvent.click(slaCheckbox);

        expect(screen.queryByText('Search Bot')).not.toBeInTheDocument();
        expect(screen.getByText('Secure Writer')).toBeInTheDocument();
    });

    it('filters agents by Authentication requirement', () => {
        render(<BrowseContent initialAgents={mockAgents} />);

        const authCheckbox = screen.getByLabelText(/Requires Authentication/i);
        fireEvent.click(authCheckbox);

        expect(screen.queryByText('Search Bot')).not.toBeInTheDocument();
        expect(screen.getByText('Secure Writer')).toBeInTheDocument();
    });

    it('shows Edge & Hardware filters when registry entries include hardware fields', () => {
        render(<BrowseContent initialAgents={mockAgents} />);

        expect(screen.getByText('Edge & Hardware')).toBeInTheDocument();
        expect(screen.getByText('Hardware class')).toBeInTheDocument();
        expect(screen.getByText('Inference mode')).toBeInTheDocument();
        expect(screen.getByText('I/O interfaces')).toBeInTheDocument();
    });

    it('filters agents by I/O multi-select', () => {
        render(<BrowseContent initialAgents={mockAgents} />);

        fireEvent.click(screen.getByText('Gpio'));

        expect(screen.getByText('Jetson Edge Demo')).toBeInTheDocument();
        expect(screen.queryByText('Search Bot')).not.toBeInTheDocument();

        fireEvent.click(screen.getByText('I2c'));

        expect(screen.getByText('Jetson Edge Demo')).toBeInTheDocument();
    });

    it('filters agents by hardware class select', () => {
        render(<BrowseContent initialAgents={mockAgents} />);

        const hardwareSelects = screen.getAllByRole('combobox');
        const hardwareClassSelect = hardwareSelects.find(
            (el) => el.closest('div')?.textContent?.includes('Hardware class')
        );
        expect(hardwareClassSelect).toBeDefined();
        fireEvent.click(hardwareClassSelect!);
        fireEvent.click(screen.getByRole('option', { name: 'Edge Accelerator' }));

        expect(screen.getByText('Jetson Edge Demo')).toBeInTheDocument();
        expect(screen.queryByText('RPi Edge Demo')).not.toBeInTheDocument();
        expect(screen.queryByText('Search Bot')).not.toBeInTheDocument();
    });

    it('filters agents by inference mode select', () => {
        render(<BrowseContent initialAgents={mockAgents} />);

        const selects = screen.getAllByRole('combobox');
        const inferenceSelect = selects.find(
            (el) => el.closest('div')?.textContent?.includes('Inference mode')
        );
        expect(inferenceSelect).toBeDefined();
        fireEvent.click(inferenceSelect!);
        fireEvent.click(screen.getByRole('option', { name: 'Local Cpu' }));

        expect(screen.getByText('RPi Edge Demo')).toBeInTheDocument();
        expect(screen.queryByText('Jetson Edge Demo')).not.toBeInTheDocument();
        expect(screen.queryByText('Search Bot')).not.toBeInTheDocument();
    });

    it('shows "No results" when search yields no matches', async () => {
        render(<BrowseContent initialAgents={mockAgents} />);

        const searchInput = screen.getByPlaceholderText('Search agents by name or description...');
        fireEvent.change(searchInput, { target: { value: 'nonexistent-agent-name' } });

        await waitFor(() => {
            expect(screen.queryByText('Search Bot')).not.toBeInTheDocument();
            expect(screen.queryByText('Secure Writer')).not.toBeInTheDocument();
            expect(screen.getByText('No agents match your criteria')).toBeInTheDocument();
        }, { timeout: 1000 });
    });
});
