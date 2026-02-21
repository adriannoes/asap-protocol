import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { VerifyForm } from '../verify-form';
import * as actions from '../actions';
import { buildVerificationRequestIssueUrl } from '@/lib/github-issues';
import type { VerificationFormValues } from '@/lib/github-issues';

vi.mock('next/link', () => ({
    default: ({ children, href }: { children: React.ReactNode; href: string }) => (
        <a href={href}>{children}</a>
    ),
}));

vi.mock('../actions', () => ({
    submitVerificationRequest: vi.fn(),
}));

const mockSubmit = vi.mocked(actions.submitVerificationRequest);

const DEFAULT_AGENT_ID = 'urn:asap:agent:username:my-agent';

function fillRequiredFields() {
    fireEvent.change(screen.getByLabelText(/Why should this agent be verified/i), {
        target: { value: 'Running in production for 3 months with 99.5% uptime.' },
    });
    fireEvent.change(screen.getByLabelText(/How long has it been running/i), {
        target: { value: '2 months' },
    });
}

describe('VerifyForm', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders the form correctly with default agent ID', () => {
        render(<VerifyForm defaultAgentId={DEFAULT_AGENT_ID} />);
        expect(screen.getByLabelText(/Agent ID \(required\)/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/Why should this agent be verified/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/How long has it been running/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/Evidence of reliability/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/Contact info/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Open GitHub Issue/i })).toBeInTheDocument();
        expect(screen.getByDisplayValue(DEFAULT_AGENT_ID)).toBeInTheDocument();
    });

    it('shows validation errors for empty required fields', async () => {
        render(<VerifyForm defaultAgentId={DEFAULT_AGENT_ID} />);

        const submitButton = screen.getByRole('button', { name: /Open GitHub Issue/i });
        fireEvent.click(submitButton);

        await waitFor(() => {
            expect(screen.getByText(/Please explain why this agent should be verified/i)).toBeInTheDocument();
            expect(screen.getByText(/Please indicate how long the agent has been running/i)).toBeInTheDocument();
        });

        expect(mockSubmit).not.toHaveBeenCalled();
    });

    it('shows validation error when agent_id is empty', async () => {
        render(<VerifyForm defaultAgentId="" />);
        fillRequiredFields();

        fireEvent.click(screen.getByRole('button', { name: /Open GitHub Issue/i }));

        await waitFor(() => {
            expect(screen.getByText(/Agent ID is required/i)).toBeInTheDocument();
        });
        expect(mockSubmit).not.toHaveBeenCalled();
    });

    it('validates why_verified min length (Zod)', async () => {
        render(<VerifyForm defaultAgentId={DEFAULT_AGENT_ID} />);
        fireEvent.change(screen.getByLabelText(/Why should this agent be verified/i), {
            target: { value: '' },
        });
        fireEvent.change(screen.getByLabelText(/How long has it been running/i), {
            target: { value: '2 months' },
        });

        fireEvent.click(screen.getByRole('button', { name: /Open GitHub Issue/i }));

        await waitFor(() => {
            expect(screen.getByText(/Please explain why this agent should be verified/i)).toBeInTheDocument();
        });
        expect(mockSubmit).not.toHaveBeenCalled();
    });

    it('validates running_since min length (Zod)', async () => {
        render(<VerifyForm defaultAgentId={DEFAULT_AGENT_ID} />);
        fireEvent.change(screen.getByLabelText(/Why should this agent be verified/i), {
            target: { value: 'Production agent with high uptime.' },
        });
        fireEvent.change(screen.getByLabelText(/How long has it been running/i), {
            target: { value: '' },
        });

        fireEvent.click(screen.getByRole('button', { name: /Open GitHub Issue/i }));

        await waitFor(() => {
            expect(screen.getByText(/Please indicate how long the agent has been running/i)).toBeInTheDocument();
        });
        expect(mockSubmit).not.toHaveBeenCalled();
    });

    it('submits valid data and opens GitHub Issue URL in new tab', async () => {
        const formValues: VerificationFormValues = {
            agent_id: DEFAULT_AGENT_ID,
            why_verified: 'Running in production for 3 months with 99.5% uptime.',
            running_since: '2 months',
        };
        const issueUrl = buildVerificationRequestIssueUrl(formValues, {
            owner: 'test-owner',
            repo: 'test-repo',
        });
        mockSubmit.mockResolvedValueOnce({ success: true, issueUrl });
        const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null);
        render(<VerifyForm defaultAgentId={DEFAULT_AGENT_ID} />);

        fillRequiredFields();
        fireEvent.click(screen.getByRole('button', { name: /Open GitHub Issue/i }));

        await waitFor(() => {
            expect(mockSubmit).toHaveBeenCalledWith({
                agent_id: DEFAULT_AGENT_ID,
                why_verified: 'Running in production for 3 months with 99.5% uptime.',
                running_since: '2 months',
            });
            expect(openSpy).toHaveBeenCalledWith(issueUrl, '_blank', 'noopener,noreferrer');
            expect(screen.getByText('Open GitHub to submit')).toBeInTheDocument();
            expect(screen.getByText('Open GitHub Issue')).toBeInTheDocument();
        });
        openSpy.mockRestore();
    });

    it('opened GitHub Issue URL matches expected template and pre-filled params', async () => {
        const formValues: VerificationFormValues = {
            agent_id: 'urn:asap:agent:user:cool-agent',
            why_verified: 'Production-ready with 99.9% uptime.',
            running_since: '3 months',
            evidence: 'https://status.example.com',
            contact: '@maintainer',
        };
        const issueUrl = buildVerificationRequestIssueUrl(formValues, {
            owner: 'asap-protocol',
            repo: 'registry',
        });
        mockSubmit.mockResolvedValueOnce({ success: true, issueUrl });
        const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null);
        render(<VerifyForm defaultAgentId={formValues.agent_id} />);

        fireEvent.change(screen.getByLabelText(/Why should this agent be verified/i), {
            target: { value: formValues.why_verified },
        });
        fireEvent.change(screen.getByLabelText(/How long has it been running/i), {
            target: { value: formValues.running_since },
        });
        fireEvent.change(screen.getByLabelText(/Evidence of reliability/i), {
            target: { value: formValues.evidence },
        });
        fireEvent.change(screen.getByLabelText(/Contact info/i), {
            target: { value: formValues.contact ?? '' },
        });

        fireEvent.click(screen.getByRole('button', { name: /Open GitHub Issue/i }));

        await waitFor(() => {
            expect(openSpy).toHaveBeenCalledWith(issueUrl, '_blank', 'noopener,noreferrer');
        });

        const openedUrl = openSpy.mock.calls[0][0];
        expect(openedUrl).toContain('/issues/new');
        expect(openedUrl).toContain('template=request_verification.yml');
        expect(openedUrl).toContain('title=Verify');
        expect(openedUrl).toContain('agent_id=');
        expect(openedUrl).toContain('why_verified=');
        expect(openedUrl).toContain('running_since=');
        expect(openedUrl).toContain('evidence=');
        expect(openedUrl).toContain('contact=');

        openSpy.mockRestore();
    });

    it('submits without optional fields (evidence, contact)', async () => {
        const submittedValues: VerificationFormValues = {
            agent_id: DEFAULT_AGENT_ID,
            why_verified: 'Running in production for 3 months with 99.5% uptime.',
            running_since: '2 months',
        };
        const issueUrl = buildVerificationRequestIssueUrl(submittedValues, {
            owner: 'owner',
            repo: 'repo',
        });
        mockSubmit.mockResolvedValueOnce({ success: true, issueUrl });
        const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null);
        render(<VerifyForm defaultAgentId={DEFAULT_AGENT_ID} />);

        fillRequiredFields();
        fireEvent.click(screen.getByRole('button', { name: /Open GitHub Issue/i }));

        await waitFor(() => {
            expect(mockSubmit).toHaveBeenCalledWith(submittedValues);
            expect(openSpy).toHaveBeenCalledWith(issueUrl, '_blank', 'noopener,noreferrer');
        });
        openSpy.mockRestore();
    });

    it('displays error alert on server action failure', async () => {
        mockSubmit.mockResolvedValueOnce({ success: false, error: 'Unauthorized' });
        render(<VerifyForm defaultAgentId={DEFAULT_AGENT_ID} />);
        fillRequiredFields();
        fireEvent.click(screen.getByRole('button', { name: /Open GitHub Issue/i }));

        await waitFor(() => {
            expect(screen.getByText('Error')).toBeInTheDocument();
            expect(screen.getByText('Unauthorized')).toBeInTheDocument();
        });
    });
});
