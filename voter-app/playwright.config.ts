import { defineConfig, devices } from '@playwright/test';

// mobile.spec.ts has its own dedicated `mobile` project (testMatch below);
// visual.spec.ts only runs via playwright.visual.config.ts's pinned Docker
// image (see that file's header). Neither belongs to the default chromium/
// firefox projects.
const EXCLUDED_FROM_DEFAULT = /(mobile|visual)\.spec\.ts$/;

export default defineConfig({
  testDir: './tests/e2e',
  // Visual regression has its own config (playwright.visual.config.ts) and its
  // own CI job, pinned to a specific Docker image for stable pixel comparisons
  // — see that file's header. Running it here too would compare Docker-
  // generated baselines against this native project's rendering, which is
  // exactly the cross-environment mismatch that setup avoids.
  //
  // NOT set here as a top-level `testIgnore`: each project below already
  // defines its own `testIgnore` (for mobile.spec.ts), and Playwright's
  // project-level testMatch/testIgnore *replaces* the top-level one for that
  // project rather than merging with it — a top-level-only entry here would
  // silently stop applying the moment any project sets its own (confirmed by
  // running `npx playwright test` and finding visual.spec.ts executing
  // against the wrong, non-Docker environment despite this line). Both
  // exclusions are combined in EXCLUDED_FROM_DEFAULT below instead, one
  // shared pattern for every project.
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
      testIgnore: EXCLUDED_FROM_DEFAULT,
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
      testIgnore: EXCLUDED_FROM_DEFAULT,
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
      testIgnore: EXCLUDED_FROM_DEFAULT,
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
