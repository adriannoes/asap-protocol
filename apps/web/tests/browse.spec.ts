import { test, expect } from '@playwright/test';

test.describe('Browse Page', () => {
    test('has Search capability and displays agents', async ({ page }) => {
        // Navigate to the browse page
        await page.goto('/browse');

        // Verify title and page header
        await expect(page).toHaveTitle(/Browse Agents/);
        await expect(page.getByRole('heading', { name: 'Agent Registry' })).toBeVisible();


        // Verify search bar is visible
        const searchInput = page.getByPlaceholder('Search agents...');
        await expect(searchInput).toBeVisible();

        // Filter tags should be visible
        await expect(page.getByRole('heading', { name: 'Skills' })).toBeVisible();
        await expect(page.getByRole('heading', { name: 'Trust Levels' })).toBeVisible();

        // Check SLA checkbox presence
        await expect(page.getByText('Has published SLA')).toBeVisible();
    });
});
