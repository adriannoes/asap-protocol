import { describe, it, expect } from 'vitest';
import { buildRegisterAgentIssueUrl } from './github-issues';
import type { ManifestFormValues } from './register-schema';

const baseValues: ManifestFormValues = {
    name: 'my-agent',
    description: 'A test agent for integration.',
    manifest_url: 'https://example.com/manifest.json',
    endpoint_http: 'https://example.com/asap',
    endpoint_ws: '',
    skills: 'search,summarize',
    built_with: '',
    repository_url: '',
    documentation_url: '',
    confirm: true,
};

describe('buildRegisterAgentIssueUrl', () => {
    it('builds URL with template and title', () => {
        const url = buildRegisterAgentIssueUrl(baseValues, { owner: 'o', repo: 'r' });
        expect(url).toContain('https://github.com/o/r/issues/new');
        expect(url).toContain('template=register_agent.yml');
        expect(url).toContain('title=Register%3A+my-agent');
    });

    it('includes all form fields as query params matching issue template ids', () => {
        const url = buildRegisterAgentIssueUrl(baseValues, { owner: 'o', repo: 'r' });
        expect(url).toContain('name=my-agent');
        expect(url).toContain('manifest_url=');
        expect(url).toContain('http_endpoint=');
        expect(url).toContain('websocket_endpoint=');
        expect(url).toContain('skills=search%2Csummarize');
        expect(url).toContain('description=');
        expect(url).toContain('built_with=');
        expect(url).toContain('repository_url=');
        expect(url).toContain('documentation_url=');
        expect(url).toContain('confirm=0');
    });

    it('encodes optional URLs and title correctly', () => {
        const withOptionals: ManifestFormValues = {
            ...baseValues,
            repository_url: 'https://github.com/user/repo',
            documentation_url: 'https://docs.example.com/agent',
        };
        const url = buildRegisterAgentIssueUrl(withOptionals, { owner: 'owner', repo: 'repo' });
        expect(url).toContain('repository_url=https%3A%2F%2Fgithub.com');
        expect(url).toContain('documentation_url=https%3A%2F%2Fdocs.example.com');
    });
});
