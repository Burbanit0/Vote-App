import { test, expect, type Page } from '@playwright/test';
import { SURFACES, ANCHORS } from './routes';

/**
 * Visual regression — screenshot baselines for the 5 real surfaces (src/routes.ts)
 * plus the two map types the Dirigeant/Assemblée toggle switches between
 * (LeaderCanvas vs ParliamentCanvas). Nothing else in the suite looks at pixels:
 * unit tests assert values, the a11y spec asserts the DOM tree, functional e2e
 * asserts testids/attributes — a map rendering visibly broken (wrong colours,
 * overlapping elements, an empty chart) passes all of them.
 *
 * Only run through playwright.visual.config.ts (see its header for why) — never
 * picked up by the default config (testIgnore there) or `npm run test:e2e`.
 *
 * The backend must be running (:4434, per CLAUDE.md): verified by hand that
 * ParliamentCanvas needs it for real — without it, it doesn't render a
 * slightly-off hemicycle, it renders its own "hémicycle indisponible"
 * fallback banner instead of one, which would make this test baseline a
 * permanently-broken-looking state that can never fail again. (LeaderCanvas's
 * default view was checked too and turned out unaffected — its win-region
 * overlay isn't computed eagerly on mount — but don't assume that holds for
 * new panels without checking; see docs/exploration/EXP-004.)
 */

// FlipReveal (components/playground/FlipReveal.tsx) floats a caption pill over
// the instrument for CAPTION_MS=2600ms on a *genuine* Dirigeant/Assemblée mode
// switch — by design, so a mode toggle mid-story is legible. It also fired,
// rarely, on a *fresh* mount in this repo's own testing (see docs/exploration/
// EXP-004 for the repro): a real once-per-run flake caught by running this
// exact suite repeatedly before trusting it, not a hypothetical worry. Rather
// than a `not.toBeVisible()` race (the caption could appear a moment later),
// wait past its entire fixed lifecycle before ever taking a playground
// screenshot, then assert it's actually gone — loud failure if that budget is
// ever wrong instead of a silently-contaminated baseline.
const FLIP_CAPTION_LIFECYCLE_MS = 3_500;

async function settleFlipCaption(page: Page): Promise<void> {
  await page.waitForTimeout(FLIP_CAPTION_LIFECYCLE_MS);
  await expect(page.locator('[data-testid="flip-caption"]')).toHaveCount(0);
}

test.describe('Visual regression — screenshot baselines', () => {
  for (const path of SURFACES) {
    test(`${path} matches its baseline`, async ({ page }) => {
      await page.goto(path);
      await expect(page.locator(ANCHORS[path])).toBeVisible();
      if (path === '/playground') await settleFlipCaption(page);
      await page.evaluate(() => document.fonts.ready);
      await expect(page).toHaveScreenshot(`surface-${path === '/' ? 'home' : path.slice(1)}.png`, {
        fullPage: true,
      });
    });
  }

  test('playground — Dirigeant mode renders the leader map (LeaderCanvas)', async ({ page }) => {
    await page.goto('/playground');
    await expect(page.locator('[data-testid="playground-page"]')).toBeVisible();
    await expect(page.locator('[data-testid="candidate-0"]')).toBeVisible();
    await settleFlipCaption(page);
    await page.evaluate(() => document.fonts.ready);
    await expect(page.locator('[data-testid="leader-canvas"]')).toHaveScreenshot(
      'playground-leader-canvas.png'
    );
  });

  test('playground — Assemblée mode renders the parliament map (ParliamentCanvas)', async ({
    page,
  }) => {
    await page.goto('/playground');
    // A genuine mode switch — FlipReveal's caption is expected here by design,
    // not just the rare fresh-mount flake; settleFlipCaption waits out either.
    await page.locator('[data-testid="mode-toggle-parliament"]').click();
    await expect(page.locator('[data-testid="party-0"]')).toBeVisible();
    await settleFlipCaption(page);
    await page.evaluate(() => document.fonts.ready);
    await expect(page.locator('[data-testid="canvas-parliament"]')).toHaveScreenshot(
      'playground-parliament-canvas.png'
    );
  });
});
