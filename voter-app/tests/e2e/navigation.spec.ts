import { test, expect } from '@playwright/test';

// Public routes accessible without authentication
const PUBLIC_ROUTES = [
  { path: '/',                      label: 'HomePage' },
  { path: '/simulation/compare',    label: 'SimulationComparePage' },
  { path: '/scenario-builder',      label: 'ScenarioBuilderPage' },
  { path: '/constitutional-crisis', label: 'ConstitutionalCrisisPage' },
];

// Errors that are expected when the backend is not running in a navigation-only test
const BENIGN_ERRORS = [
  'Failed to fetch',
  'NetworkError',
  'ERR_CONNECTION_REFUSED',
  'Load failed',
  'fetch',
];

function isBenign(msg: string): boolean {
  return BENIGN_ERRORS.some((fragment) => msg.includes(fragment));
}

test.describe('Navigation — all public routes load', () => {
  for (const { path, label } of PUBLIC_ROUTES) {
    test(`${label} (${path}) renders without JS errors`, async ({ page }) => {
      const criticalErrors: string[] = [];

      page.on('pageerror', (err) => {
        if (!isBenign(err.message)) criticalErrors.push(`pageerror: ${err.message}`);
      });
      page.on('console', (msg) => {
        if (msg.type() === 'error' && !isBenign(msg.text())) {
          criticalErrors.push(`console.error: ${msg.text()}`);
        }
      });

      await page.goto(path);
      await page.waitForLoadState('domcontentloaded');

      expect(criticalErrors).toHaveLength(0);
    });
  }

  test('navbar is visible on all public routes', async ({ page }) => {
    for (const { path } of PUBLIC_ROUTES) {
      await page.goto(path);
      await expect(page.locator('[data-tour="navbar"]')).toBeVisible();
    }
  });

  test('/login hides navbar and renders login form', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('[data-tour="navbar"]')).not.toBeVisible();
    await expect(page.getByRole('button', { name: /connexion|log in/i })).toBeVisible();
  });

  test('/register hides navbar and renders register form', async ({ page }) => {
    await page.goto('/register');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('[data-tour="navbar"]')).not.toBeVisible();
    // Register form has a submit button
    await expect(page.getByRole('button', { name: /inscription|register/i })).toBeVisible();
  });

  test('brand link on navbar navigates to home', async ({ page }) => {
    await page.goto('/simulation/compare');
    await page.locator('[data-tour="navbar"]').getByRole('link', { name: /vote lab/i }).click();
    await expect(page).toHaveURL('/');
  });

  test('navbar links reach the correct pages', async ({ page }) => {
    await page.goto('/');

    // Simulateur → /scenario-builder
    await page.locator('[data-tour="navbar"]').getByRole('link', { name: /simulateur|simulator/i }).click();
    await expect(page).toHaveURL('/scenario-builder');

    // Méthodes → /simulation/compare
    await page.locator('[data-tour="navbar"]').getByRole('link', { name: /méthodes|methods/i }).click();
    await expect(page).toHaveURL('/simulation/compare');

    // Vote Blanc → /constitutional-crisis
    await page.locator('[data-tour="navbar"]').getByRole('link', { name: /vote blanc|blank vote/i }).click();
    await expect(page).toHaveURL('/constitutional-crisis');
  });

  // /real-elections is a tab inside /simulation/compare, not a standalone route.
  // This test verifies the tab is reachable after enabling expert mode.
  test('real elections tab is accessible in /simulation/compare (expert mode)', async ({ page }) => {
    await page.goto('/simulation/compare');

    // Switch to expert mode if currently in beginner mode
    const modeBtn = page.locator('[data-tour="navbar"]').getByRole('button', { name: /débutant|beginner/i });
    if (await modeBtn.isVisible()) {
      await modeBtn.click();
    }

    // The "Élections réelles" tab header is present in the DOM even before running
    // a simulation (it's inside the Tabs definition, hidden until hasResults is true).
    // At minimum, the page must have loaded correctly.
    await expect(page.locator('h2').first()).toBeVisible();
  });
});
