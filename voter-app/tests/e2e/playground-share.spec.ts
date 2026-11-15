import { test, expect, type Page } from './coverageFixtures';

// A scenario as a link: the button writes it, opening it in a fresh browser shows the same
// moment and hands the visitor a way back to their own scenario.
//
// The clipboard is refused here on purpose: the link then shows in a field, which every browser
// lets a test read, whereas clipboard permissions are Chromium-only.

const NOTICE = '[data-testid="shared-scenario-notice"]';

async function shareFromStrategy(page: Page): Promise<string> {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: () => Promise.reject(new Error('denied')) },
      configurable: true,
    });
  });
  await page.goto('/playground');
  await page.locator('[data-testid="moment-strategy"]').click();
  await expect(page.locator('[data-testid="moment-strategy-panel"]')).toBeVisible();
  await page.locator('[data-testid="share-scenario"]').click();
  const link = await page.locator('[data-testid="share-scenario-manual"]').inputValue();
  expect(link).toContain('#s=');
  return link;
}

test.describe('Playground — scenario link', () => {
  test('a link opens in a fresh browser on the moment it was made in, and Back restores', async ({
    page,
    browser,
  }) => {
    const link = await shareFromStrategy(page);

    const stranger = await browser.newContext();
    try {
      const other = await stranger.newPage();
      await other.goto(link);
      await expect(other.locator('[data-testid="moment-strategy-panel"]')).toBeVisible();
      await expect(other.locator(NOTICE)).toBeVisible();
      // The link is gone from the address, so a reload does not apply it again.
      expect(new URL(other.url()).hash).toBe('');

      await other.locator('[data-testid="shared-scenario-restore"]').click();
      await expect(other.locator(NOTICE)).toBeHidden();
      await expect(other.locator('[data-testid="moment-electorate-panel"]')).toBeVisible();
    } finally {
      await stranger.close();
    }
  });

  test('a link pasted into the tab that is already open is opened too', async ({ page }) => {
    const link = await shareFromStrategy(page);
    await page.locator('[data-testid="moment-bilan"]').click();
    await expect(page.locator('[data-testid="moment-bilan-panel"]')).toBeVisible();

    // Same page, another hash: the browser does not reload, it only fires hashchange.
    await page.goto(link);
    await expect(page.locator('[data-testid="moment-strategy-panel"]')).toBeVisible();
    await expect(page.locator(NOTICE)).toBeVisible();

    await page.locator('[data-testid="shared-scenario-keep"]').click();
    await expect(page.locator(NOTICE)).toBeHidden();
    await expect(page.locator('[data-testid="moment-strategy-panel"]')).toBeVisible();
  });

  test('a link that is not a scenario changes nothing', async ({ page }) => {
    await page.goto('/playground#s=not-a-scenario');
    await expect(page.locator('[data-testid="moment-electorate-panel"]')).toBeVisible();
    await expect(page.locator(NOTICE)).toHaveCount(0);
  });
});
