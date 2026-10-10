import { test, expect } from './coverageFixtures';
import { SURFACES, ANCHORS, assertEverySurfaceAnchored, settled } from './routes';

// Runs only on the `mobile` project (see playwright.config.ts — an Android
// device profile, chromium-based: WebKit's iOS emulation needs system deps
// this environment doesn't have, and the rendering *engine* difference is
// already covered by the `webkit` desktop project — this file is about the
// mobile *viewport and interaction model* (narrow width, touch, the collapsed
// navbar), not a second engine pass). Desktop projects ignore this file (see
// `testIgnore` on chromium/firefox/webkit) — running it at desktop width
// would just assert the wrong things about a nav that isn't collapsed there.

test.describe('Mobile viewport — the six real surfaces', () => {
  test('every surface in src/routes.ts is covered here', () => {
    expect(assertEverySurfaceAnchored).not.toThrow();
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
    const nav = page.locator('[data-testid="navbar"]');
    await expect(page.getByTestId('navbar-toggle')).toBeVisible();
    // The links are still in the DOM (collapsed via CSS, not unmounted) —
    // what proves the collapse is that they aren't reachable until expanded.
    // Scoped to the navbar: the home page also has its own in-body
    // "Playground" link, ambiguous against an unscoped page-wide locator.
    await expect(nav.getByRole('link', { name: /playground/i })).not.toBeVisible();
  });

  test('the collapsed navbar opens on tap and can navigate', async ({ page }) => {
    await page.goto('/');
    await settled(page, '/');
    const nav = page.locator('[data-testid="navbar"]');
    await page.getByTestId('navbar-toggle').click();
    await expect(nav.getByRole('link', { name: /playground/i })).toBeVisible();

    await nav.getByRole('link', { name: /playground/i }).click();
    await expect(page).toHaveURL(/\/playground$/);
    // Clicking a link inside the collapsed menu closes it again (Navbar.tsx's
    // onClick={() => setNavExpanded(false)}) — the next surface starts collapsed.
    await expect(nav.getByRole('link', { name: /laboratoire/i })).not.toBeVisible();
    await settled(page, '/playground');
  });

  test('the playground instrument is usable at mobile width', async ({ page }) => {
    await page.goto('/playground');
    await expect(page.locator('[data-testid="playground-page"]')).toBeVisible();
    // The moment rail is the primary mobile interaction surface for this
    // page — confirm it's actually reachable, not just present off-screen.
    await expect(page.locator('[data-testid="moment-method"]')).toBeInViewport();
  });

  test('/polity fits a phone: no sideways scroll, and the player and map respond to taps', async ({
    page,
  }) => {
    await page.goto('/polity');
    await expect(page.getByTestId('polity-map-canvas')).toBeVisible();
    await expect(page.getByTestId('timeline-svg')).toBeVisible();
    await expect
      .poll(() =>
        page.evaluate(
          () => document.documentElement.scrollWidth - document.documentElement.clientWidth
        )
      )
      .toBeLessThanOrEqual(2);

    await page.getByTestId('player-step-forward').tap();
    await expect.poll(() => new URL(page.url()).searchParams.get('tick')).toBe('1');
    await page.getByTestId('polity-lens-party').tap();
    await expect.poll(() => new URL(page.url()).searchParams.get('lens')).toBe('party');
  });

  // The story test below was flaky on loaded runners: the paradox readout's placeholder fitted
  // on one line and the rate, arriving after the test's scroll, wrapped it onto a second, pushing
  // the map down. Held until measured, the reply must leave the readout's height as it was.
  test("the paradox rate arriving does not change its readout's height", async ({ page }) => {
    let release = () => {};
    const held = new Promise<void>((resolve) => (release = resolve));
    await page.route('**/api/v2/election/profile-simulate', async (route) => {
      await held;
      await route.continue();
    });
    await page.goto('/playground');
    const rate = page.getByTestId('cycle-rate');
    await expect(rate).toBeVisible();
    // The monospace font decides the wrap: measure once it has loaded, not in the fallback.
    await page.evaluate(() => document.fonts.ready);
    const before = (await rate.boundingBox())!.height;
    release();
    await expect(rate).toHaveText(/\d %$/);
    expect((await rate.boundingBox())!.height).toBe(before);
  });

  // spoiler's first beat is short; paradox's 4th (393 characters in French) is the longest.
  for (const [story, beats] of [
    ['spoiler', 0],
    ['paradox', 3],
  ] as const) {
    test(`a story keeps its narration and the map on screen together: ${story} (W3.4)`, async ({
      page,
    }) => {
      await page.goto('/playground');
      await page.getByTestId('story-launch').tap();
      await page.getByTestId(`story-pick-${story}`).tap();
      for (let i = 0; i < beats; i++) await page.getByTestId('story-next').tap();
      const nav = page.getByTestId('navbar');
      const bar = page.getByTestId('story-bar');
      const beat = page.getByTestId('story-beat');
      const map = page.getByTestId('leader-map');
      await expect(beat).toBeVisible();

      // Scroll the page until the map's bottom is just above the screen's, as a reader
      // would. (scrollIntoView can move the visual viewport instead of the page on a phone.)
      await map.evaluate((el) =>
        window.scrollBy(0, el.getBoundingClientRect().bottom - innerHeight + 8)
      );
      // innerHeight, not viewportSize(): the page measures in its own CSS pixels, which
      // differ from the device's when the browser zooms out to fit a wider layout.
      const height = await page.evaluate(() => innerHeight);
      const box = async (l: typeof map) => (await l.boundingBox())!;
      // Share of a box inside the screen.
      const shown = async (l: typeof map) => {
        const b = await box(l);
        return (Math.min(b.y + b.height, height) - Math.max(b.y, 0)) / b.height;
      };
      await expect.poll(() => shown(beat)).toBeGreaterThan(0.99);
      await expect.poll(() => shown(map)).toBeGreaterThan(0.99);
      // Nothing covers anything: the bar sits under the navbar, the map under the bar.
      const [n, b, m] = [await box(nav), await box(bar), await box(map)];
      expect(b.y).toBeGreaterThanOrEqual(n.y + n.height - 1);
      expect(m.y).toBeGreaterThanOrEqual(b.y + b.height - 1);

      if (story === 'spoiler') {
        // On the next beat, without scrolling again. The press is a plain click: tap() would
        // first scroll the page back to the sticky button's place in the flow, which a
        // finger does not. The browser's scroll anchoring then holds the map in place
        // while the beat and the winner strip above it grow.
        await page.getByTestId('story-next').dispatchEvent('click');
        await expect.poll(() => shown(beat)).toBeGreaterThan(0.99);
        await expect.poll(() => shown(map)).toBeGreaterThan(0.99);
      }
    });
  }
});
