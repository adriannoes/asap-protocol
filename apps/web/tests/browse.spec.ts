import { test, expect } from '@playwright/test';

test.describe('Browse Page', () => {
    test('has Search capability and displays agents', async ({ page }) => {
        await page.goto('/browse');

        await expect(page).toHaveTitle(/Browse Agents/);
        await expect(page.getByRole('heading', { name: 'Agent Registry' })).toBeVisible();

        const searchInput = page.getByPlaceholder('Search agents...');
        await expect(searchInput).toBeVisible();

        await expect(page.getByRole('heading', { name: 'Skills' })).toBeVisible();
        await expect(page.getByRole('heading', { name: 'Trust Levels' })).toBeVisible();

        await expect(page.getByText('Has published SLA')).toBeVisible();
    });
});
