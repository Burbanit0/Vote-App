import { test, expect } from '@playwright/test';
import {
  SURFACES,
  LEGACY_REDIRECTS,
  ANCHORS,
  concreteUrl,
  assertEverySurfaceAnchored,
} from './routes';

// The route lists come from src/routes.ts — the same table App.tsx renders. A
// route added or retired there changes this suite in the same commit; that is
// the mechanism that keeps these tests honest.

test.describe('Navigation — the five real surfaces', () => {
  test('every surface in src/routes.ts is covered here', () => {
    assertEverySurfaceAnchored();
  });

  for (const path of SURFACES) {
    test(`${path} renders its own screen without a JS crash`, async ({ page }) => {
      // Uncaught exceptions only. console.error is dev-build noise (React warnings,
      // aborted fetches) and made the old suite red for unrelated reasons.
      const crashes: string[] = [];
      page.on('pageerror', (err) => crashes.push(err.message));

      await page.goto(path);
      await expect(page.locator(ANCHORS[path])).toBeVisible();
      expect(crashes).toEqual([]);
    });
  }

  test('navbar is visible on every surface', async ({ page }) => {
    for (const path of SURFACES) {
      await page.goto(path);
      await expect(page.locator('[data-tour="navbar"]')).toBeVisible();
    }
  });

  test('navbar links reach the three destinations', async ({ page }) => {
    const nav = () => page.locator('[data-tour="navbar"]');

    await page.goto('/');
    await nav()
      .getByRole('link', { name: /playground/i })
      .click();
    await expect(page).toHaveURL(/\/playground$/);

    await nav()
      .getByRole('link', { name: /laboratoire/i })
      .click();
    await expect(page).toHaveURL(/\/laboratoire$/);

    await nav()
      .getByRole('link', { name: /à vous de jouer|your turn/i })
      .click();
    await expect(page).toHaveURL(/\/a-vous-de-jouer$/);
  });

  test('brand link goes back home', async ({ page }) => {
    await page.goto('/playground');
    await page
      .locator('[data-tour="navbar"]')
      .getByRole('link', { name: /vote lab/i })
      .click();
    await expect(page).toHaveURL(/\/$/);
  });

  for (const [from, to] of Object.entries(LEGACY_REDIRECTS)) {
    test(`${from} redirects to ${to}`, async ({ page }) => {
      await page.goto(concreteUrl(from));
      await expect(page).toHaveURL(new RegExp(`${to.replace(/\//g, '\\/')}$`));
    });
  }

  test('an unknown URL renders the 404 page', async ({ page }) => {
    await page.goto('/cette-page-nexiste-pas');
    await expect(page.getByText('404')).toBeVisible();
  });

  test('dark mode is set from the settings menu and survives a reload', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('html')).toHaveAttribute('data-bs-theme', 'light');

    // The theme switch lives inside the ⚙ Préférences dropdown, not the navbar.
    await page.locator('#user-settings-dropdown').click();
    await page.getByRole('button', { name: /mode sombre|dark mode/i }).click();
    await expect(page.locator('html')).toHaveAttribute('data-bs-theme', 'dark');

    await page.reload();
    await expect(page.locator('html')).toHaveAttribute('data-bs-theme', 'dark');
  });
});
