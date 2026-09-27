import { defineConfig, devices } from '@playwright/test';

import e2e from './playwright.config';

/**
 * Visual regression (screenshot) tests — split out from playwright.config.ts on
 * purpose. Pixel comparisons are only meaningful when the baseline PNGs and the
 * run comparing against them were rendered by byte-identical font/AA/GPU-vs-
 * software rasterization — the *same host OS image* isn't enough to guarantee
 * that on its own (see docs/exploration/EXP-004 for what was actually tried).
 *
 * The fix adopted here: baselines are generated, and CI compares against them,
 * **only** inside the exact Playwright Docker image pinned to this repo's
 * `@playwright/test` version (`mcr.microsoft.com/playwright:v<version>-noble` —
 * see `.github/workflows/e2e.yml`'s `visual-regression` job and
 * `npm run test:visual:docker`). Running this config on a bare host (a
 * contributor's laptop, or `npm run test:e2e`'s native CI job) is fine for a
 * quick local look but its diffs are not authoritative — only the Docker run is.
 *
 * The backend must also be running (:4434, per CLAUDE.md) — checked by hand,
 * not assumed: ParliamentCanvas genuinely needs it (a fallback banner instead
 * of a real hemicycle otherwise), even though LeaderCanvas's default view
 * doesn't. See visual.spec.ts's header and docs/exploration/EXP-004.
 */
// Everything else -- testDir, retries, timeout, baseURL, locale, the
// production-build webServer -- is the e2e suite's own.
export default defineConfig({
  ...e2e,
  testMatch: '**/visual.spec.ts',
  reporter: [['html', { outputFolder: 'playwright-report-visual' }], ['list']],

  // No `maxDiffPixelRatio`/`maxDiffPixels` tolerance: Playwright's own default
  // (any pixel past the per-pixel colour `threshold` fails the comparison) is
  // what actually gets used. A 0.01 ratio was tried first and turned out to be
  // the wrong call — verified by hand, not assumed: it silently let a single
  // recoloured candidate marker (a small fraction of a full-page or even a
  // canvas-scoped screenshot) through as a "pass" (see docs/exploration/
  // EXP-004). A tolerance loose enough to survive environment noise is loose
  // enough to hide exactly the kind of localized regression this item exists
  // to catch — pinning the Docker environment (this file's header) is what
  // earns the zero-tolerance comparison, not a percentage-based fudge factor.

  use: {
    ...e2e.use,
    // Freezes the JS-driven animations that already honour this media query
    // (DiscoverVoteAnimation, CampaignTimeline, LeaderScene3D, RegimeGlobe —
    // grep `prefers-reduced-motion` under src/) on their end state instead of
    // mid-flight. CSS animations/transitions are handled separately by
    // `toHaveScreenshot`'s own default `animations: 'disabled'`, which fast-
    // forwards finite ones and cancels infinite ones — no per-test wiring needed.
    reducedMotion: 'reduce',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
