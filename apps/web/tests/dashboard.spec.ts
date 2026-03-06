import { test, expect } from '@playwright/test';

test.describe('Dashboard (Authenticated)', () => {
    test.beforeEach(async ({ page }) => {
        // Use the test login endpoint to bypass NextAuth OAuth flow
        // The ENABLE_FIXTURE_ROUTES environment variable must be set
        await page.goto('/api/auth/test-login?username=e2e-tester-no-agents');
        // The endpoint automatically redirects to /dashboard
    });

    test('should display empty state when user has no agents', async ({ page }) => {
        await expect(page).toHaveURL(/\/dashboard/);
        await expect(page.getByRole('heading', { name: 'Developer Dashboard' })).toBeVisible();

        // Check for the "No agents found" empty state
        await expect(page.getByRole('heading', { name: 'No agents found' })).toBeVisible();
        await expect(page.getByText(/You haven't registered any agents/)).toBeVisible();

        // Check tabs
        await expect(page.getByRole('tab', { name: /My Agents/ })).toBeVisible();
        await expect(page.getByRole('tab', { name: 'Usage Metrics' })).toBeVisible();
        await expect(page.getByRole('tab', { name: 'API Keys' })).toBeVisible();

        // Navigate to register page via empty state button
        const registerButton = page.getByRole('link', { name: 'Register your first agent' });
        await expect(registerButton).toBeVisible();
        await registerButton.click();

        await expect(page).toHaveURL(/\/dashboard\/register/);
        await expect(page.getByRole('heading', { name: 'Register New Agent' })).toBeVisible();
    });
});
