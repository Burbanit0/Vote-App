import { test, expect } from '@playwright/test';

// The app is anonymous and has exactly five surfaces (see App.tsx). Everything
// else is a redirect kept alive for old links. Anchors are data-testids owned by
// the pages themselves, so a route that renders an empty shell fails here.
const ROUTES = [
  { path: '/', name: 'HomePage', anchor: '[data-tour="hero"]' },
  { path: '/playground', name: 'PlaygroundPage', anchor: '[data-testid="playground-page"]' },
  { path: '/laboratoire', name: 'LaboratoirePage', anchor: '[data-testid="lab-family-rail"]' },
  { path: '/decouvrir', name: 'DecouvrirPage', anchor: '[data-testid="discover-winner"]' },
  { path: '/a-vous-de-jouer', name: 'AVousDeJouerPage', anchor: '[data-testid="play-vote-open"]' },
];

// Redirects declared in App.tsx — the retired surfaces. Kept as a test because
// these URLs are in the wild (shared links, search engines).
const REDIRECTS: [from: string, to: string][] = [
  ['/simulation/compare', '/playground'],
  ['/scenario-builder', '/playground'],
  ['/campagne', '/playground'],
  ['/election-lab', '/playground'],
  ['/theory', '/laboratoire'],
  ['/quiz', '/laboratoire'],
  ['/login', '/'],
  ['/profile', '/'],
];

test.describe('Navigation — the five real surfaces', () => {
  for (const { path, name, anchor } of ROUTES) {
    test(`${name} (${path}) renders its own screen without a JS crash`, async ({ page }) => {
      // Uncaught exceptions only. console.error is dev-build noise (React warnings,
      // aborted fetches) and made the old suite red for unrelated reasons.
      const crashes: string[] = [];
      page.on('pageerror', (err) => crashes.push(err.message));

      await page.goto(path);
      await expect(page.locator(anchor)).toBeVisible();
      expect(crashes).toEqual([]);
    });
  }

  test('navbar is visible on every surface', async ({ page }) => {
    for (const { path } of ROUTES) {
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

  for (const [from, to] of REDIRECTS) {
    test(`${from} redirects to ${to}`, async ({ page }) => {
      await page.goto(from);
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
