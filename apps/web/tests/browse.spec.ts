import { test, expect } from '@playwright/test';

test.describe('Browse Page', () => {
    test('has Search capability and displays agents', async ({ page }) => {
        await page.goto('/browse');

        await expect(page).toHaveTitle(/Browse Agents/);
        await expect(page.getByRole('heading', { name: 'Agent Registry' })).toBeVisible();

        // Verify search bar is visible (use data-testid to avoid strict mode when multiple tables)
        await expect(page.getByTestId('data-table-search').first()).toBeVisible();

        // Verify DataTable renders (use .first() when multiple instances exist)
        await expect(page.getByTestId('data-table').first()).toBeVisible();

        // Verify table has header row with expected columns
        const dataTable = page.getByTestId('data-table').first();
        await expect(dataTable.getByRole('columnheader', { name: /Name/i })).toBeVisible();
        await expect(dataTable.getByRole('columnheader', { name: /Status/i })).toBeVisible();

        // Filter tags should be visible (use .first() when multiple instances exist)
        await expect(page.getByRole('heading', { name: 'Skills' }).first()).toBeVisible();
        await expect(page.getByRole('heading', { name: 'Trust Levels' }).first()).toBeVisible();

        // Check SLA checkbox presence (use .first() when multiple instances exist)
        await expect(page.getByText('Has published SLA').first()).toBeVisible();
    });

    test('can sort agents by name', async ({ page }) => {
        await page.goto('/browse');
        const dataTable = page.getByTestId('data-table').first();
        const nameButton = dataTable.getByRole('button', { name: 'Name' });
        await nameButton.click();
        // Verify sort indicator appears (data-sort-direction for reliable E2E)
        const nameHeader = dataTable.getByRole('columnheader', { name: /Name/i });
        await expect(nameHeader).toHaveAttribute('data-sort-direction', /(ascending|descending)/);
    });

    test('shows pagination controls', async ({ page }) => {
        await page.goto('/browse');
        await expect(page.getByTestId('data-table-pagination').first()).toBeVisible();
    });
});
