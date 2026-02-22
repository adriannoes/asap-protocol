import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { RegisterAgentForm } from '../register-form';
import * as actions from '../actions';
import { buildRegisterAgentIssueUrl } from '@/lib/github-issues';
import type { ManifestFormValues } from '@/lib/register-schema';

// Mock Next.js Link
vi.mock('next/link', () => ({
    default: ({ children, href }: { children: React.ReactNode, href: string }) => <a href={href}>{children}</a>
}));

// Mock the server action
vi.mock('../actions', () => ({
    submitAgentRegistration: vi.fn()
}));

const mockSubmit = vi.mocked(actions.submitAgentRegistration);

function fillValidFields() {
    fireEvent.change(screen.getByLabelText(/Agent Slug Name/i), { target: { value: 'cool-agent' } });
    fireEvent.change(screen.getByRole('textbox', { name: /Manifest URL/i }), { target: { value: 'https://example.com/manifest' } });
    fireEvent.change(screen.getByLabelText(/Short Description/i), { target: { value: 'This is a description that is long enough' } });
    fireEvent.change(screen.getByLabelText(/HTTP Endpoint/i), { target: { value: 'https://example.com/api' } });
    fireEvent.change(screen.getByLabelText(/Skills/i), { target: { value: 'search, write' } });
}

describe('RegisterAgentForm', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders the form correctly', () => {
        render(<RegisterAgentForm />);
        expect(screen.getByLabelText(/Agent Slug Name/i)).toBeInTheDocument();
        expect(screen.getByRole('textbox', { name: /Manifest URL/i })).toBeInTheDocument();
        expect(screen.getByLabelText(/Short Description/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/HTTP Endpoint/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/Skills/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/^Built with/i)).toBeInTheDocument();
        expect(screen.getByRole('textbox', { name: /Repository URL/i })).toBeInTheDocument();
        expect(screen.getByRole('textbox', { name: /Documentation URL/i })).toBeInTheDocument();
        expect(screen.getByRole('checkbox')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Submit Registration/i })).toBeInTheDocument();
    });

    it('shows validation errors for empty submission', async () => {
        render(<RegisterAgentForm />);

        const submitButton = screen.getByRole('button', { name: /Submit Registration/i });
        fireEvent.click(submitButton);

        // Zod validation messages (required fields; confirm may be among them)
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

    it('validates manifest URL format (Zod URL constraint)', async () => {
        render(<RegisterAgentForm />);
        fillValidFields();
        fireEvent.change(screen.getByRole('textbox', { name: /Manifest URL/i }), { target: { value: 'not-a-valid-url' } });
        fireEvent.click(screen.getByRole('checkbox'));

        fireEvent.click(screen.getByRole('button', { name: /Submit Registration/i }));

        await waitFor(() => {
            expect(screen.getByText(/Must be a valid URL starting with http/i)).toBeInTheDocument();
        });
        expect(mockSubmit).not.toHaveBeenCalled();
    });

    it('validates description min length (Zod)', async () => {
        render(<RegisterAgentForm />);
        fireEvent.change(screen.getByLabelText(/Agent Slug Name/i), { target: { value: 'cool-agent' } });
        fireEvent.change(screen.getByRole('textbox', { name: /Manifest URL/i }), { target: { value: 'https://example.com/manifest' } });
        fireEvent.change(screen.getByLabelText(/Short Description/i), { target: { value: 'short' } });
        fireEvent.change(screen.getByLabelText(/HTTP Endpoint/i), { target: { value: 'https://example.com/api' } });
        fireEvent.change(screen.getByLabelText(/Skills/i), { target: { value: 'search' } });
        fireEvent.click(screen.getByRole('checkbox'));

        fireEvent.click(screen.getByRole('button', { name: /Submit Registration/i }));

        await waitFor(() => {
            const errors = screen.getAllByText(/String must contain at least|Too small/i);
            expect(errors.length).toBeGreaterThan(0);
        });
        expect(mockSubmit).not.toHaveBeenCalled();
    });

    it('validates confirmation checkbox is required (Zod)', async () => {
        render(<RegisterAgentForm />);
        fillValidFields();
        // do not check the confirm checkbox

        fireEvent.click(screen.getByRole('button', { name: /Submit Registration/i }));

        await waitFor(() => {
            expect(mockSubmit).not.toHaveBeenCalled();
        });
        const checkbox = screen.getByRole('checkbox');
        expect(checkbox).not.toBeChecked();
    });

    it('submits valid data and opens GitHub Issue URL in new tab', async () => {
        const issueUrl = 'https://github.com/owner/repo/issues/new?template=register_agent.yml&title=Register%3A+cool-agent';
        mockSubmit.mockResolvedValueOnce({ success: true, issueUrl });
        const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null);
        render(<RegisterAgentForm />);

        fillValidFields();
        fireEvent.click(screen.getByRole('checkbox'));

        fireEvent.click(screen.getByRole('button', { name: /Submit Registration/i }));

        await waitFor(() => {
            expect(mockSubmit).toHaveBeenCalledWith({
                name: 'cool-agent',
                manifest_url: 'https://example.com/manifest',
                description: 'This is a description that is long enough',
                endpoint_http: 'https://example.com/api',
                endpoint_ws: '',
                skills: 'search, write',
                built_with: '',
                repository_url: '',
                documentation_url: '',
                confirm: true,
            });
            expect(openSpy).toHaveBeenCalledWith(issueUrl, '_blank', 'noopener,noreferrer');
            expect(screen.getByText('Open GitHub to submit')).toBeInTheDocument();
            expect(screen.getByText('Open GitHub Issue')).toBeInTheDocument();
        });
        openSpy.mockRestore();
    });

    it('opened GitHub Issue URL matches expected template and pre-filled params', async () => {
        const formValues: ManifestFormValues = {
            name: 'my-agent',
            description: 'A test agent for integration.',
            manifest_url: 'https://example.com/manifest.json',
            endpoint_http: 'https://example.com/asap',
            endpoint_ws: '',
            skills: 'search,summarize',
            built_with: 'CrewAI',
            repository_url: 'https://github.com/u/r',
            documentation_url: 'https://docs.example.com',
            confirm: true,
        };
        const issueUrl = buildRegisterAgentIssueUrl(formValues, { owner: 'test-owner', repo: 'test-repo' });
        mockSubmit.mockResolvedValueOnce({ success: true, issueUrl });
        const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null);
        render(<RegisterAgentForm />);

        fireEvent.change(screen.getByLabelText(/Agent Slug Name/i), { target: { value: formValues.name } });
        fireEvent.change(screen.getByRole('textbox', { name: /Manifest URL/i }), { target: { value: formValues.manifest_url } });
        fireEvent.change(screen.getByLabelText(/Short Description/i), { target: { value: formValues.description } });
        fireEvent.change(screen.getByLabelText(/HTTP Endpoint/i), { target: { value: formValues.endpoint_http } });
        fireEvent.change(screen.getByLabelText(/Skills/i), { target: { value: formValues.skills } });
        fireEvent.change(screen.getByLabelText(/^Built with/i), { target: { value: formValues.built_with } });
        fireEvent.change(screen.getByRole('textbox', { name: /Repository URL/i }), { target: { value: formValues.repository_url } });
        fireEvent.change(screen.getByRole('textbox', { name: /Documentation URL/i }), { target: { value: formValues.documentation_url } });
        fireEvent.click(screen.getByRole('checkbox'));

        fireEvent.click(screen.getByRole('button', { name: /Submit Registration/i }));

        await waitFor(() => {
            expect(openSpy).toHaveBeenCalledWith(issueUrl, '_blank', 'noopener,noreferrer');
        });

        const openedUrl = openSpy.mock.calls[0][0];
        expect(openedUrl).toContain('/issues/new');
        expect(openedUrl).toContain('template=register_agent.yml');
        expect(openedUrl).toContain('title=Register');
        expect(openedUrl).toContain('name=my-agent');
        expect(openedUrl).toContain('http_endpoint=');
        expect(openedUrl).toContain('manifest_url=');
        expect(openedUrl).toContain('skills=');
        expect(openedUrl).toContain('built_with=CrewAI');
        expect(openedUrl).toContain('repository_url=');
        expect(openedUrl).toContain('documentation_url=');

        openSpy.mockRestore();
    });

    it('displays error alert on server action failure', async () => {
        mockSubmit.mockResolvedValueOnce({ success: false, error: 'GitHub API limits reached.' });
        render(<RegisterAgentForm />);
        fillValidFields();
        fireEvent.click(screen.getByRole('checkbox'));
        fireEvent.click(screen.getByRole('button', { name: /Submit Registration/i }));

        await waitFor(() => {
            expect(screen.getByText('Error')).toBeInTheDocument();
            expect(screen.getByText('GitHub API limits reached.')).toBeInTheDocument();
        });
    });
});
