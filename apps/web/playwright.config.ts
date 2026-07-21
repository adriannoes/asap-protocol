import { defineConfig, devices } from '@playwright/test';

// Resolve NodeJS warnings about conflicting color environment variables
delete process.env.NO_COLOR;
delete process.env.FORCE_COLOR;

const webServerEnv = { ...process.env };

/** Browser install troubleshooting: apps/web/docs/playwright-e2e.md. */
export default defineConfig({
  testDir: './tests',
  testIgnore: '**/load/**',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:3000',

    trace: 'on-first-retry',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },

    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },

    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },

    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
  ],

  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    env: {
      ...webServerEnv,
      ENABLE_FIXTURE_ROUTES: 'true',
      // Use fixture registry for E2E so dashboard Bento test can assert with agents
      REGISTRY_URL: 'http://localhost:3000/api/fixtures/registry?count=10',
    },
  },
});
