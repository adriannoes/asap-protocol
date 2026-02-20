import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { RegisterAgentForm } from '../register-form';
import * as actions from '../actions';

// Mock Next.js Link
vi.mock('next/link', () => ({
    default: ({ children, href }: { children: React.ReactNode, href: string }) => <a href={href}>{children}</a>
}));

// Mock the server action
vi.mock('../actions', () => ({
    submitAgentRegistration: vi.fn()
}));

const mockSubmit = vi.mocked(actions.submitAgentRegistration);

describe('RegisterAgentForm', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders the form correctly', () => {
        render(<RegisterAgentForm />);
        expect(screen.getByLabelText(/Agent Slug Name/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/Manifest URL/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/Short Description/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/HTTP Endpoint/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/Skills/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Submit Registration/i })).toBeInTheDocument();
    });

    it('shows validation errors for empty submission', async () => {
        render(<RegisterAgentForm />);

        const submitButton = screen.getByRole('button', { name: /Submit Registration/i });
        fireEvent.click(submitButton);

        // Zod validation messages
        await waitFor(() => {
            const lengthErrors = screen.getAllByText(/(String must contain at least|Too small)/i);
            expect(lengthErrors.length).toBeGreaterThan(0);
            expect(screen.getByText(/Must be a valid URL starting with http/i)).toBeInTheDocument();
            expect(screen.getByText(/At least one skill is required/i)).toBeInTheDocument();
        });

        expect(mockSubmit).not.toHaveBeenCalled();
    });

    it('validates custom regex on name field', async () => {
        render(<RegisterAgentForm />);

        const nameInput = screen.getByLabelText(/Agent Slug Name/i);
        fireEvent.change(nameInput, { target: { value: 'Invalid Name With Spaces' } });

        const submitButton = screen.getByRole('button', { name: /Submit Registration/i });
        fireEvent.click(submitButton);

        await waitFor(() => {
            expect(screen.getByText(/Name can only contain lowercase letters, numbers, and hyphens/i)).toBeInTheDocument();
        });

        expect(mockSubmit).not.toHaveBeenCalled();
    });

    it('submits valid data to the server action', async () => {
        mockSubmit.mockResolvedValueOnce({ success: true, prUrl: 'https://github.com/pr/1' });
        render(<RegisterAgentForm />);

        fireEvent.change(screen.getByLabelText(/Agent Slug Name/i), { target: { value: 'cool-agent' } });
        fireEvent.change(screen.getByLabelText(/Manifest URL/i), { target: { value: 'https://example.com/manifest' } });
        fireEvent.change(screen.getByLabelText(/Short Description/i), { target: { value: 'This is a description that is long enough' } });
        fireEvent.change(screen.getByLabelText(/HTTP Endpoint/i), { target: { value: 'https://example.com/api' } });
        fireEvent.change(screen.getByLabelText(/Skills/i), { target: { value: 'search, write' } });

        const submitButton = screen.getByRole('button', { name: /Submit Registration/i });
        fireEvent.click(submitButton);

        await waitFor(() => {
            expect(mockSubmit).toHaveBeenCalledWith({
                name: 'cool-agent',
                manifest_url: 'https://example.com/manifest',
                description: 'This is a description that is long enough',
                endpoint_http: 'https://example.com/api',
                endpoint_ws: '',
                skills: 'search, write'
            });
            expect(screen.getByText('Registration Submitted!')).toBeInTheDocument();
            expect(screen.getByText('View Pull Request on GitHub')).toBeInTheDocument();
        });
    });

    it('displays error alert on server action failure', async () => {
        mockSubmit.mockResolvedValueOnce({ success: false, error: 'GitHub API limits reached.' });
        render(<RegisterAgentForm />);

        fireEvent.change(screen.getByLabelText(/Agent Slug Name/i), { target: { value: 'cool-agent' } });
        fireEvent.change(screen.getByLabelText(/Manifest URL/i), { target: { value: 'https://example.com/manifest' } });
        fireEvent.change(screen.getByLabelText(/Short Description/i), { target: { value: 'This is a description that is long enough' } });
        fireEvent.change(screen.getByLabelText(/HTTP Endpoint/i), { target: { value: 'https://example.com/api' } });
        fireEvent.change(screen.getByLabelText(/Skills/i), { target: { value: 'search, write' } });

        const submitButton = screen.getByRole('button', { name: /Submit Registration/i });
        fireEvent.click(submitButton);

        await waitFor(() => {
            expect(screen.getByText('Error')).toBeInTheDocument();
            expect(screen.getByText('GitHub API limits reached.')).toBeInTheDocument();
        });
    });
});
