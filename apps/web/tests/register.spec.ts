import { test, expect } from '@playwright/test';

test.describe('Register Agent (Authenticated)', () => {
    test.beforeEach(async ({ page }) => {
        // Authenticate as a test user
        await page.goto('/api/auth/test-login?username=e2e-tester');
    });

    test('should allow user to fill and submit agent registration', async ({ page, context }) => {
        await page.goto('/dashboard/register');
        await expect(page).toHaveTitle(/Register Agent \| Developer Dashboard/);

        // Fill out the form
        await page.getByLabel(/Agent Slug Name/i).fill('e2e-awesome-agent');
        await page.getByRole('textbox', { name: /Manifest URL/i }).fill('https://example.com/manifest.json');
        await page.getByLabel(/Short Description/i).fill('This is an awesome agent created by Playwright E2E tests.');
        await page.getByLabel(/HTTP Endpoint/i).fill('https://example.com/asap');
        await page.getByLabel(/Skills/i).fill('testing, playwright');
        await page.getByRole('textbox', { name: /Repository URL/i }).fill('https://github.com/asap-protocol/e2e');
        await page.getByRole('textbox', { name: /Documentation URL/i }).fill('https://example.com/docs');

        // Check the consent box
        await page.getByRole('checkbox').check();

        // Click the submit button
        await page.getByRole('button', { name: /Submit Registration/i }).click();

        // Ensure success state in original page
        await expect(page.getByText('Open GitHub to submit')).toBeVisible();

        // Instead of dealing with popups, verify the fallback link's href is correct
        const githubLink = page.getByRole('link', { name: /Open GitHub Issue/i });
        await expect(githubLink).toBeVisible();
        const href = await githubLink.getAttribute('href');
        expect(href).toBeTruthy();

        // Verify it points to GitHub Issues with correct params
        const decodedUrl = decodeURIComponent(href!);
        expect(decodedUrl).toContain('github.com');
        expect(decodedUrl).toContain('issues/new');
        expect(decodedUrl).toContain('e2e-awesome-agent');
        expect(decodedUrl).toContain('public_key='); // Verify WebCrypto Public Key is generated and attached
    });
});
