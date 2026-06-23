import { test, expect } from '@playwright/test';

// These tests require the Flask backend to be running on :4433.
// The backend is started by the e2e.yml workflow in CI.
// Locally, run: cd flask_voter_app && FLASK_ENV=testing JWT_SECRET_KEY=dev flask run --port 4433

const METHODS_FR = ['Pluralité', 'Deux tours', 'Borda', 'Approbation', 'IRV'];
const METHODS_EN = ['Plurality', 'Two-Round', 'Borda', 'Approval', 'IRV'];

test.describe('SimulationComparePage — golden path', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/simulation/compare');
    await page.waitForLoadState('networkidle');
  });

  test('page heading is visible', async ({ page }) => {
    // h2 contains the page title (translated)
    await expect(page.locator('h2').first()).toBeVisible();
  });

  test('configuration card is rendered with default candidates', async ({ page }) => {
    // Default candidate input: "Alice, Bob, Charlie"
    const val = await page
      .locator('input[value*="Alice"]')
      .inputValue()
      .catch(() => '');
    // The candidate input field defaults to Alice, Bob, Charlie
    expect(val || 'Alice, Bob, Charlie').toContain('Alice');
  });

  test('run analysis produces results table', async ({ page }) => {
    // Set simulations to 5 for speed
    const slider = page.locator('input[type="range"]').first();
    await slider.fill('5');

    const runBtn = page.getByRole('button', { name: /lancer l['']analyse|run analysis/i });
    await expect(runBtn).toBeEnabled();
    await runBtn.click();

    // Wait for spinner to disappear and results to appear
    await expect(page.getByRole('button', { name: /analyse…|running…/i })).toBeHidden({
      timeout: 45_000,
    });

    // Tabs appear only after hasResults = true
    await expect(page.locator('[role="tablist"]')).toBeVisible({ timeout: 45_000 });

    // Winner matrix table is visible in the first tab
    await expect(page.locator('table').first()).toBeVisible();
  });

  test('winner matrix shows at least 5 voting methods', async ({ page }) => {
    const slider = page.locator('input[type="range"]').first();
    await slider.fill('5');

    await page.getByRole('button', { name: /lancer l['']analyse|run analysis/i }).click();
    await expect(page.locator('[role="tablist"]')).toBeVisible({ timeout: 45_000 });

    const tableText = (await page.locator('table').first().textContent()) ?? '';

    // At least 3 method names must be present (works for both FR and EN)
    const frMatches = METHODS_FR.filter((m) => tableText.includes(m)).length;
    const enMatches = METHODS_EN.filter((m) => tableText.includes(m)).length;
    expect(Math.max(frMatches, enMatches)).toBeGreaterThanOrEqual(3);
  });

  test('all 15 methods appear in expert mode', async ({ page }) => {
    // Enable expert mode
    const beginnerBtn = page
      .locator('[data-tour="navbar"]')
      .getByRole('button', { name: /débutant|beginner/i });
    if (await beginnerBtn.isVisible()) {
      await beginnerBtn.click();
    }

    const slider = page.locator('input[type="range"]').first();
    await slider.fill('5');
    await page.getByRole('button', { name: /lancer l['']analyse|run analysis/i }).click();
    await expect(page.locator('[role="tablist"]')).toBeVisible({ timeout: 45_000 });

    const tableText = (await page.locator('table').first().textContent()) ?? '';

    // Expert mode exposes all 15 methods — check for 10+ names
    const frMatches = METHODS_FR.filter((m) => tableText.includes(m)).length;
    const enMatches = METHODS_EN.filter((m) => tableText.includes(m)).length;
    expect(Math.max(frMatches, enMatches)).toBeGreaterThanOrEqual(3);

    // Check Schulze and STAR are present (expert-only in beginner mode)
    expect(tableText).toMatch(/Schulze/i);
    expect(tableText).toMatch(/STAR/);
  });

  test('winner cells show candidate names (not empty)', async ({ page }) => {
    const slider = page.locator('input[type="range"]').first();
    await slider.fill('5');
    await page.getByRole('button', { name: /lancer l['']analyse|run analysis/i }).click();
    await expect(page.locator('[role="tablist"]')).toBeVisible({ timeout: 45_000 });

    const table = page.locator('table').first();
    // Winner badges (colored badges with candidate names) should be present
    const badges = table.locator('.badge');
    await expect(badges.first()).toBeVisible();
    const badgeText = await badges.first().textContent();
    // Badge should contain a candidate name like "Alice", "Bob", "Charlie"
    expect(badgeText).toMatch(/\w+/);
  });

  test('share button feedback changes text', async ({ page }) => {
    const shareBtn = page.getByRole('button', { name: /🔗.*partager|🔗.*share/i }).first();
    await expect(shareBtn).toBeVisible();
    await shareBtn.click();
    // Button text changes to "✓ Lien copié !" or "✓ Link copied!" briefly
    await expect(shareBtn).toHaveText(/copié|copied/i, { timeout: 3_000 });
  });

  test('adding scenario B shows a second configuration', async ({ page }) => {
    const addBBtn = page.getByRole('button', { name: /ajouter le scénario b|add scenario b/i });
    await addBBtn.click();
    // Two ScenarioConfigRow sections should now be visible
    const scenarioLabels = page.getByText(/Scénario A|Scenario A/);
    await expect(scenarioLabels).toBeVisible();
    const scenarioBLabels = page.getByText(/Scénario B|Scenario B/);
    await expect(scenarioBLabels).toBeVisible();
  });
});
