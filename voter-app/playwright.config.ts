import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  // Visual regression has its own config (playwright.visual.config.ts) and its
  // own CI job, pinned to a specific Docker image for stable pixel comparisons
  // — see that file's header. Running it here too would compare Docker-
  // generated baselines against this native project's rendering, which is
  // exactly the cross-environment mismatch that setup avoids.
  testIgnore: '**/visual.spec.ts',
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
      testIgnore: /mobile\.spec\.ts$/,
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
      testIgnore: /mobile\.spec\.ts$/,
    },
    // Android (chromium-based), not an iPhone preset: iOS emulation needs
    // WebKit, whose *rendering engine* is already covered by a desktop pass
    // elsewhere — this project is about the mobile *viewport + touch
    // interaction model* (narrow width, collapsed navbar), not a second
    // engine. Scoped to mobile.spec.ts only via testMatch — running the full
    // desktop-oriented suite at this width would assert the wrong things
    // about UI (like the navbar) that only differs below the lg breakpoint.
    {
      name: 'mobile',
      use: { ...devices['Galaxy S24'] },
      testMatch: /mobile\.spec\.ts$/,
    },
  ],

  webServer: {
    command: 'npm start',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
