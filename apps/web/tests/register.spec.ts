import { test, expect } from '@playwright/test';

test.describe('Register Agent (Authenticated)', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/api/auth/test-login?username=e2e-tester');
    });

    test('should allow user to fill and submit agent registration', async ({ page }) => {
        await page.goto('/dashboard/register');
        await expect(page).toHaveTitle(/Register Agent \| Developer Dashboard/);

        const firstInput = page.getByLabel(/Agent Slug Name/i);
        await expect(firstInput).toBeVisible({ timeout: 5000 });
        await expect(page.getByTestId('canvas-bg')).toBeVisible({ timeout: 10_000 });

        await page.getByLabel(/Agent Slug Name/i).fill('e2e-awesome-agent');
        await page.getByRole('textbox', { name: /Manifest URL/i }).fill('https://example.com/manifest.json');
        await page.getByLabel(/Short Description/i).fill('This is an awesome agent created by Playwright E2E tests.');
        await page.getByLabel(/HTTP Endpoint/i).fill('https://example.com/asap');
        await page.getByLabel(/Skills/i).fill('testing, playwright');
        await page.getByRole('textbox', { name: /Repository URL/i }).fill('https://github.com/asap-protocol/e2e');
        await page.getByRole('textbox', { name: /Documentation URL/i }).fill('https://example.com/docs');

        await page.getByRole('checkbox').check();
        await page.getByRole('button', { name: /Submit Registration/i }).click();

        await expect(page.getByText('Open GitHub to submit')).toBeVisible();
        const githubLink = page.getByRole('link', { name: /Open GitHub Issue/i });
        await expect(githubLink).toBeVisible();
        const href = await githubLink.getAttribute('href');
        expect(href).toBeTruthy();

        const decodedUrl = decodeURIComponent(href!);
        expect(decodedUrl).toContain('github.com');
        expect(decodedUrl).toContain('issues/new');
        expect(decodedUrl).toContain('e2e-awesome-agent');
        expect(decodedUrl).toContain('public_key=');
    });
});
