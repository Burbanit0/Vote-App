/**
 * coverageFixtures.ts — thin wrapper around `@playwright/test`'s `test` that
 * dumps each test's Istanbul coverage to disk after the test finishes.
 *
 * Why a wrapper instead of a global hook: Playwright only runs
 * beforeEach/afterEach for tests created from the *same* extended `test`
 * instance — there's no config-level "run this after every test in every
 * file" mechanism. Every e2e spec therefore imports `test`/`expect` from
 * here instead of directly from '@playwright/test'.
 *
 * Runtime coverage under e2e (Lot 6, PLAN_SOLIDITE_TECHNIQUE.md): when
 * E2E_COVERAGE=true, vite.config.ts instruments src/** with Istanbul
 * counters and exposes them as `window.__coverage__` in the running app.
 * Playwright gives each test a fresh page (and often a fresh browser
 * context), so that object would otherwise vanish at the end of every
 * single test — this fixture reads it back out and writes one JSON blob
 * per test into .nyc_output/, which `scripts/e2e_coverage.sh` later merges
 * with `nyc merge` into one aggregate report.
 *
 * Zero behavioural change when E2E_COVERAGE is unset (the normal case for
 * every PR run): the fixture still attaches (so this file works as a
 * drop-in replacement for '@playwright/test' either way) but skips the
 * page.evaluate() + disk write entirely.
 */
import { test as base, expect } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const COVERAGE_DIR = join(process.cwd(), '.nyc_output');
const coverageEnabled = process.env.E2E_COVERAGE === 'true';

export const test = base.extend<{ collectCoverage: void }>({
  // `auto: true` — every test collects coverage without each spec having to
  // request the fixture explicitly (they only ever destructure `page`).
  collectCoverage: [
    async ({ page }, use, testInfo) => {
      await use();
      if (!coverageEnabled) return;
      try {
        const coverage = await page.evaluate(
          () => (window as unknown as { __coverage__?: unknown }).__coverage__
        );
        if (!coverage) return;
        mkdirSync(COVERAGE_DIR, { recursive: true });
        writeFileSync(join(COVERAGE_DIR, `${testInfo.testId}.json`), JSON.stringify(coverage));
      } catch {
        // Page already closed/navigated cross-origin by the time this runs —
        // losing one test's slice doesn't invalidate the aggregate report.
      }
    },
    { auto: true },
  ],
});

export { expect };
export type { Page } from '@playwright/test';
