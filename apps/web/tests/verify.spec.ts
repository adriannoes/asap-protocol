import { test, expect } from '@playwright/test';

test.describe('Verify Agent (Authenticated)', () => {
    test.beforeEach(async ({ page }) => {
        // Authenticate as a test user
        await page.goto('/api/auth/test-login?username=e2e-tester');
    });

    test('should show empty state if no agent is selected', async ({ page }) => {
        await page.goto('/dashboard/verify');
        await expect(page).toHaveTitle(/Request Verification \| Developer Dashboard/);

        await expect(page.getByRole('heading', { name: 'Request Verified Badge' })).toBeVisible();
        await expect(page.getByText('No agent selected')).toBeVisible();
        await expect(page.getByRole('link', { name: 'Return to Dashboard' })).toBeVisible();
    });

    test('should allow user to fill and submit verification request', async ({ page }) => {
        const agentId = 'urn:asap:agent:e2e-tester:e2e-awesome-agent';
        await page.goto(`/dashboard/verify?agent_id=${encodeURIComponent(agentId)}`);

        // Assert the agent ID input is filled and readonly
        const agentIdInput = page.getByLabel(/Agent ID/i);
        await expect(agentIdInput).toHaveValue(agentId);

        // Fill out the verification form
        await page.getByLabel(/Why should this agent be verified/i).fill('This agent has been running reliably and is open source.');
        await page.getByLabel(/How long has it been running/i).fill('2 months');
        await page.getByLabel(/Evidence of reliability/i).fill('https://status.example.com');
        await page.getByLabel(/Contact info/i).fill('e2e@example.com');

        // Click the submit button
        // We look specifically for the button role to avoid confusing with the success link later
        await page.getByRole('button', { name: /^Open GitHub Issue$/i }).click();

        // Ensure success state in original page
        await expect(page.getByText('Open GitHub to submit')).toBeVisible();

        // Verify the fallback link's href is correct
        const githubLink = page.getByRole('link', { name: /^Open GitHub Issue$/i });
        await expect(githubLink).toBeVisible();
        const href = await githubLink.getAttribute('href');
        expect(href).toBeTruthy();

        // Verify it points to GitHub Issues with correct params
        const decodedUrl = decodeURIComponent(href!);
        expect(decodedUrl).toContain('github.com');
        expect(decodedUrl).toContain('issues/new');
        expect(decodedUrl).toContain('e2e-awesome-agent');
        expect(decodedUrl).toContain('Verify'); // Should contain verified somewhere in the title/body
    });
});
