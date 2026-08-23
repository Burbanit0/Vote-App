import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false, // simulations are CPU-heavy
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  // Fail fast: no test here legitimately needs 30s (the slowest, the Laboratoire
  // sweeps, raise it themselves). A stale selector should cost seconds, not a
  // minute — the old suite hid its rot behind 60s timeouts until the whole job
  // was killed at the 25-minute mark with no report.
  timeout: 30_000,
  // json feeds scripts/check-flaky.mjs: with retries on, a test that only passes
  // on the second attempt is reported green and its rot stays invisible.
  reporter: [['html'], ['list'], ['json', { outputFile: 'playwright-report/results.json' }]],

  use: {
    baseURL: 'http://localhost:3000',
    locale: 'fr-FR', // consistent French UI across all tests
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
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
  ],

  webServer: {
    command: 'npm start',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
