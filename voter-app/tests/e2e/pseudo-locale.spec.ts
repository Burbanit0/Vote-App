import { test, expect } from './coverageFixtures';
import { SURFACES, ANCHORS } from './routes';

// Pseudo-locale sweep (Lot 7, PLAN_SOLIDITE_TECHNIQUE.md): every visible
// string is ~35% longer and accented (see src/i18n/pseudoize.ts) — this
// catches layout overflow/truncation before a real second language, or a
// future one, exposes it for real. `votelab_lang` in localStorage is the
// same key `i18next-browser-languagedetector` reads on init
// (src/i18n/index.ts), so seeding it before the app boots is enough to
// activate the pseudo bundle — no UI language switcher needed (`pseudo` is
// intentionally not offered there).
//
// The pseudo strings are wrapped in `⟦...⟧` specifically so a test can wait
// for the bundle to actually be active (not just the French fallback still
// rendering) before checking layout.

const OVERFLOW_TOLERANCE_PX = 2; // scrollbar/subpixel rounding slack

test.describe('pseudo-locale layout sweep', () => {
  for (const path of SURFACES) {
    test(`${path} has no page-level horizontal overflow in pseudo-locale`, async ({ page }) => {
      await page.addInitScript(() => {
        localStorage.setItem('votelab_lang', 'pseudo');
      });
      await page.goto(path);
      await expect(page.locator(ANCHORS[path])).toBeVisible();
      await page.waitForFunction(() => document.body.innerText.includes('⟦'));

      const overflow = await page.evaluate(() => {
        const root = document.documentElement;
        return root.scrollWidth - root.clientWidth;
      });
      expect(
        overflow,
        `${path}: page is ${overflow}px wider than the viewport in pseudo-locale`
      ).toBeLessThanOrEqual(OVERFLOW_TOLERANCE_PX);
    });
  }
});
