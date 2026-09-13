import { test, expect } from './coverageFixtures';
import { SURFACES, ANCHORS, assertEverySurfaceAnchored } from './routes';

// Runs only on the `mobile` project (see playwright.config.ts — an Android
// device profile, chromium-based: WebKit's iOS emulation needs system deps
// this environment doesn't have, and the rendering *engine* difference is
// already covered by the `webkit` desktop project — this file is about the
// mobile *viewport and interaction model* (narrow width, touch, the collapsed
// navbar), not a second engine pass). Desktop projects ignore this file (see
// `testIgnore` on chromium/firefox/webkit) — running it at desktop width
// would just assert the wrong things about a nav that isn't collapsed there.

test.describe('Mobile viewport — the five real surfaces', () => {
  test('every surface in src/routes.ts is covered here', () => {
    assertEverySurfaceAnchored();
  });

  for (const path of SURFACES) {
    test(`${path} renders its own screen without a JS crash`, async ({ page }) => {
      const crashes: string[] = [];
      page.on('pageerror', (err) => crashes.push(err.message));

      await page.goto(path);
      await expect(page.locator(ANCHORS[path])).toBeVisible();
      expect(crashes).toEqual([]);
    });
  }

  test('the navbar collapses behind a toggle below the lg breakpoint', async ({ page }) => {
    await page.goto('/');
    const nav = page.locator('[data-tour="navbar"]');
    await expect(page.getByTestId('navbar-toggle')).toBeVisible();
    // The links are still in the DOM (collapsed via CSS, not unmounted) —
    // what proves the collapse is that they aren't reachable until expanded.
    // Scoped to the navbar: the home page also has its own in-body
    // "Playground" link, ambiguous against an unscoped page-wide locator.
    await expect(nav.getByRole('link', { name: /playground/i })).not.toBeVisible();
  });

  test('the collapsed navbar opens on tap and can navigate', async ({ page }) => {
    await page.goto('/');
    const nav = page.locator('[data-tour="navbar"]');
    await page.getByTestId('navbar-toggle').click();
    await expect(nav.getByRole('link', { name: /playground/i })).toBeVisible();

    await nav.getByRole('link', { name: /playground/i }).click();
    await expect(page).toHaveURL(/\/playground$/);
    // Clicking a link inside the collapsed menu closes it again (Navbar.tsx's
    // onClick={() => setNavExpanded(false)}) — the next surface starts collapsed.
    await expect(nav.getByRole('link', { name: /laboratoire/i })).not.toBeVisible();
  });

  test('the playground instrument is usable at mobile width', async ({ page }) => {
    await page.goto('/playground');
    await expect(page.locator('[data-testid="playground-page"]')).toBeVisible();
    // The moment rail is the primary mobile interaction surface for this
    // page — confirm it's actually reachable, not just present off-screen.
    await expect(page.locator('[data-testid="moment-method"]')).toBeInViewport();
  });
});
