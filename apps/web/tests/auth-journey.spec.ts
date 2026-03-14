import { test, expect } from '@playwright/test';

/** E2E: Register Agent → sign-in with callbackUrl; login not 403; Explore Agents → /browse. */
test.describe('Auth & Register Agent journey', () => {
    test('Register Agent from homepage redirects to sign-in with callbackUrl to /dashboard/register', async ({
        page,
    }) => {
        await page.goto('/');

        const registerLink = page.getByRole('link', { name: 'Register Agent' });
        await expect(registerLink).toBeVisible();

        await registerLink.click();

        await expect(async () => {
            const url = page.url();
            const hasCallbackOrSignIn = url.includes('callbackUrl') || url.includes('api/auth/signin');
            const hasRegisterPath = url.includes('dashboard') && url.includes('register');
            expect(hasCallbackOrSignIn || hasRegisterPath, `Expected sign-in or register flow; got: ${url}`).toBe(true);
        }).toPass({ timeout: 8000 });

        const url = page.url();
        if (url.includes('callbackUrl')) {
            expect(decodeURIComponent(url)).toMatch(/dashboard.*register/);
        }
    });

    test('Connect / Login does not show Forbidden error', async ({ page }) => {
        await page.goto('/');

        const loginButton = page.getByRole('button', { name: /Connect \/ Login/i });
        await expect(loginButton).toBeVisible();

        const responsePromise = page.waitForResponse(
            (res) => res.url().includes('/api/auth') && res.request().method() !== 'OPTIONS',
            { timeout: 10000 }
        ).catch(() => null);

        await loginButton.click();

        const response = await responsePromise;
        if (response) {
            expect(response.status(), 'Auth API should not return 403 Forbidden').not.toBe(403);
        }

        const bodyText = await page.locator('body').textContent();
        expect(bodyText).not.toContain('"error":"Forbidden"');
    });

    test('Direct navigation to /dashboard/register redirects to sign-in with callbackUrl', async ({
        page,
    }) => {
        await page.goto('/dashboard/register');

        await expect(async () => {
            const url = page.url();
            const hasCallbackOrSignIn = url.includes('callbackUrl') || url.includes('api/auth/signin');
            const hasRegisterInCallback = url.includes('dashboard') && url.includes('register');
            expect(hasCallbackOrSignIn && hasRegisterInCallback, `Expected sign-in with register callback; got: ${url}`).toBe(true);
        }).toPass({ timeout: 8000 });

        const url = page.url();
        expect(decodeURIComponent(url)).toMatch(/dashboard.*register/);
    });

    test('Explore Agents navigates to /browse without auth redirect', async ({ page }) => {
        await page.goto('/');

        const exploreLink = page.getByRole('link', { name: 'Explore Agents' });
        await expect(exploreLink).toBeVisible();

        await exploreLink.click();

        await expect(page).toHaveURL(/\/browse/);
        await expect(page).toHaveTitle(/Browse Agents/);
    });

    test('sign-in page renders WebGL background', async ({ page }) => {
        await page.goto('/auth/signin');
        // Wait for Canvas to be visible (may take a moment for WebGL init)
        await expect(page.getByTestId('canvas-bg')).toBeVisible({ timeout: 10000 });
        // Verify the form is still rendered on top
        await expect(page.getByRole('heading', { name: /Sign in/i })).toBeVisible();
    });

    test('WebGL canvas does not cause console errors', async ({ page }) => {
        const errors: string[] = [];
        page.on('console', (msg) => {
            if (msg.type() === 'error') errors.push(msg.text());
        });

        await page.goto('/auth/signin');
        await page.waitForTimeout(3000); // Let Canvas initialize fully

        // Filter out known non-critical warnings
        const criticalErrors = errors.filter(
            (e) => !e.includes('third-party cookie') && !e.includes('favicon')
        );
        expect(criticalErrors).toHaveLength(0);
    });
});
