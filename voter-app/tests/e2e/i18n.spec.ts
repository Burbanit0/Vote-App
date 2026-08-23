import { test, expect, type Page } from '@playwright/test';

// The app ships FR (source of truth) and EN, and i18next renders a missing key
// as the key itself. These tests walk both languages over every surface and fail
// on any leaked key — the failure mode unit tests cannot see, because they only
// assert the keys they already know about.

const ROUTES = [
  { path: '/', anchor: '[data-tour="hero"]' },
  { path: '/playground', anchor: '[data-testid="playground-page"]' },
  { path: '/laboratoire', anchor: '[data-testid="lab-family-rail"]' },
  { path: '/decouvrir', anchor: '[data-testid="discover-winner"]' },
  { path: '/a-vous-de-jouer', anchor: '[data-testid="play-vote-open"]' },
];

// The namespaces actually used in the UI. A visible "moments.method.label" means
// the key is missing from the active language.
const NAMESPACES = [
  'nav',
  'moments',
  'masthead',
  'instrument',
  'canvas',
  'electorate',
  'composer',
  'method',
  'strategy',
  'bilan',
  'lab',
  'discover',
  'play',
  'blankVote',
  'realElection',
  'parliament',
  'presets',
  'axes',
  'rules',
  'timeline',
  'home',
  'story',
];
const KEY_LEAK = new RegExp(`\\b(?:${NAMESPACES.join('|')})\\.[a-zA-Z][\\w]*(?:\\.[\\w]+)*`, 'g');

async function leakedKeys(page: Page): Promise<string[]> {
  const text = await page.locator('body').innerText();
  return [...new Set(text.match(KEY_LEAK) ?? [])];
}

async function switchToEnglish(page: Page) {
  await page.locator('#user-settings-dropdown').click();
  await page.getByRole('button', { name: /switch to english/i }).click();
}

test.describe('i18n', () => {
  test('the language switch changes the UI and survives a reload', async ({ page }) => {
    await page.goto('/');
    const nav = page.locator('[data-tour="navbar"]');
    await expect(nav).toContainText('Laboratoire');

    await switchToEnglish(page);
    await expect(nav.getByRole('link', { name: /your turn/i })).toBeVisible();

    await page.reload();
    await expect(nav.getByRole('link', { name: /your turn/i })).toBeVisible();
  });

  for (const { path, anchor } of ROUTES) {
    test(`${path} shows no untranslated key in French`, async ({ page }) => {
      await page.goto(path);
      await expect(page.locator(anchor)).toBeVisible();
      expect(await leakedKeys(page), `raw i18n keys visible on ${path} (fr)`).toEqual([]);
    });
  }

  for (const { path, anchor } of ROUTES) {
    test(`${path} shows no untranslated key in English`, async ({ page }) => {
      await page.goto('/');
      await switchToEnglish(page);
      await page.goto(path);
      await expect(page.locator(anchor)).toBeVisible();
      expect(await leakedKeys(page), `raw i18n keys visible on ${path} (en)`).toEqual([]);
    });
  }
});
