import { test, expect } from '@playwright/test';

test.describe('Dashboard (Authenticated)', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/api/auth/test-login?username=e2e-tester-no-agents');
    });

    test('should display empty state when user has no agents', async ({ page }, testInfo) => {
        await expect(page).toHaveURL(/\/dashboard/);
        await expect(page.getByRole('heading', { name: 'Developer Dashboard' })).toBeVisible();

        const isMobile = testInfo.project.name === 'Mobile Chrome';
        if (isMobile) {
            await expect(page.getByTestId('app-sidebar')).toBeHidden();
        } else {
            await expect(page.getByTestId('app-sidebar')).toBeVisible();
            await expect(page.getByTestId('sidebar-link-dashboard')).toBeVisible();
            await expect(page.getByTestId('sidebar-link-browse')).toBeVisible();
            await expect(page.getByTestId('sidebar-link-register')).toBeVisible();
        }

        await expect(page.getByRole('heading', { name: 'No agents found' })).toBeVisible();
        await expect(page.getByText(/You haven't registered any agents/)).toBeVisible();

        await expect(page.getByRole('tab', { name: /My Agents/ })).toBeVisible();
        await expect(page.getByRole('tab', { name: 'Usage Metrics' })).toBeVisible();
        await expect(page.getByRole('tab', { name: 'API Keys' })).toBeVisible();

        const registerButton = page.getByRole('link', { name: 'Register your first agent' });
        await expect(registerButton).toBeVisible();
        await registerButton.click();

        await expect(page).toHaveURL(/\/dashboard\/register/);
        await expect(page.getByRole('heading', { name: 'Register New Agent' })).toBeVisible();
    });

    test('can navigate via sidebar', async ({ page }, testInfo) => {
        await expect(page).toHaveURL(/\/dashboard/);
        if (testInfo.project.name === 'Mobile Chrome') {
            await page.getByTestId('sidebar-mobile-trigger').click();
        }
        await page.getByTestId('sidebar-link-browse').click();
        await expect(page).toHaveURL(/\/browse/);
    });

    test('mobile: sidebar triggers via hamburger menu', async ({ page }) => {
        await page.setViewportSize({ width: 375, height: 812 });
        await page.goto('/api/auth/test-login?username=e2e-tester-no-agents');

        await expect(page.getByTestId('app-sidebar')).toBeHidden();

        await page.getByTestId('sidebar-mobile-trigger').click();

        await expect(page.getByTestId('app-sidebar')).toBeVisible();
    });

    test('can toggle sidebar via keyboard shortcut', async ({ page }, testInfo) => {
        if (testInfo.project.name === 'Mobile Chrome') return;
        await expect(page).toHaveURL(/\/dashboard/);
        const sidebar = page.locator('[data-slot="sidebar"]').first();
        await expect(sidebar).toHaveAttribute('data-state', 'expanded');
        const modKey = process.platform === 'darwin' ? 'Meta' : 'Control';
        await page.keyboard.press(`${modKey}+b`);
        await expect(sidebar).toHaveAttribute('data-state', 'collapsed');
        await page.keyboard.press(`${modKey}+b`);
        await expect(sidebar).toHaveAttribute('data-state', 'expanded');
    });
});
