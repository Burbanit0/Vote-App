import { test, expect } from '@playwright/test';

test.describe('Dark mode', () => {
  test.beforeEach(async ({ page }) => {
    // Start with a fresh localStorage — light mode by default
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
  });

  test('default theme is light', async ({ page }) => {
    const htmlTheme = await page.locator('html').getAttribute('data-bs-theme');
    // Either 'light' explicitly, or absent (which defaults to light)
    expect(htmlTheme === 'dark').toBe(false);
  });

  test('clicking 🌙 sets data-bs-theme="dark" on <html>', async ({ page }) => {
    const toggleBtn = page.getByRole('button', { name: /passer en mode sombre|switch to dark/i });
    await expect(toggleBtn).toBeVisible();
    await toggleBtn.click();

    // ThemeContext calls document.documentElement.setAttribute('data-bs-theme', 'dark')
    await expect(page.locator('html')).toHaveAttribute('data-bs-theme', 'dark');
  });

  test('dark mode icon changes from 🌙 to ☀️', async ({ page }) => {
    const toggleBtn = page.getByRole('button', { name: /passer en mode sombre|switch to dark/i });
    await toggleBtn.click();

    // After switching, button now offers to go back to light mode
    await expect(
      page.getByRole('button', { name: /passer en mode clair|switch to light/i })
    ).toBeVisible();
  });

  test('navbar background changes in dark mode', async ({ page }) => {
    const navbar = page.locator('[data-tour="navbar"]');

    // Light mode background
    const lightBg = await navbar.evaluate((el) =>
      window.getComputedStyle(el).backgroundColor
    );

    // Switch to dark mode
    await page.getByRole('button', { name: /passer en mode sombre|switch to dark/i }).click();
    await page.waitForTimeout(200); // allow CSS transition

    // Dark mode background
    const darkBg = await navbar.evaluate((el) =>
      window.getComputedStyle(el).backgroundColor
    );

    // The computed background color must differ between light and dark
    expect(lightBg).not.toEqual(darkBg);
  });

  test('toggling back to light restores data-bs-theme="light"', async ({ page }) => {
    // Switch to dark
    await page.getByRole('button', { name: /passer en mode sombre|switch to dark/i }).click();
    await expect(page.locator('html')).toHaveAttribute('data-bs-theme', 'dark');

    // Switch back to light
    await page.getByRole('button', { name: /passer en mode clair|switch to light/i }).click();
    await expect(page.locator('html')).toHaveAttribute('data-bs-theme', 'light');
  });

  test('theme preference is persisted in localStorage', async ({ page }) => {
    // Switch to dark
    await page.getByRole('button', { name: /passer en mode sombre|switch to dark/i }).click();

    // Read localStorage key used by ThemeContext
    const stored = await page.evaluate(() => localStorage.getItem('votelab_theme'));
    expect(stored).toBe('dark');
  });

  test('dark mode is preserved on page reload', async ({ page }) => {
    // Switch to dark
    await page.getByRole('button', { name: /passer en mode sombre|switch to dark/i }).click();
    await expect(page.locator('html')).toHaveAttribute('data-bs-theme', 'dark');

    // Reload page — ThemeContext reads from localStorage
    await page.reload();
    await page.waitForLoadState('domcontentloaded');

    await expect(page.locator('html')).toHaveAttribute('data-bs-theme', 'dark');
  });

  test('dark mode applies consistently across routes', async ({ page }) => {
    // Enable dark mode on home
    await page.getByRole('button', { name: /passer en mode sombre|switch to dark/i }).click();
    await expect(page.locator('html')).toHaveAttribute('data-bs-theme', 'dark');

    // Navigate to simulation page — theme must persist
    await page.goto('/simulation/compare');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('html')).toHaveAttribute('data-bs-theme', 'dark');

    // Navigate to scenario builder — theme must persist
    await page.goto('/scenario-builder');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('html')).toHaveAttribute('data-bs-theme', 'dark');
  });

  test('FR/EN language toggle works alongside dark mode', async ({ page }) => {
    // Switch language
    const langBtn = page.getByRole('button', { name: /^FR$|^EN$/ });
    await expect(langBtn).toBeVisible();
    const initialLang = await langBtn.textContent();
    await langBtn.click();

    const newLang = await langBtn.textContent();
    expect(newLang).not.toEqual(initialLang);

    // Switch dark mode — both toggles must coexist without error
    const darkToggle = page.getByRole('button', {
      name: /passer en mode sombre|switch to dark|passer en mode clair|switch to light/i,
    });
    await darkToggle.click();
    await expect(page.locator('html')).toHaveAttribute('data-bs-theme', 'dark');
  });
});
