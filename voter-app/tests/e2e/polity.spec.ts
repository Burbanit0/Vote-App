import { test, expect } from './coverageFixtures';

// The run explorer (/polity), against the backend's committed fixture run: the
// e2e backend starts with POLITY_RUN_ROOTS unset, so the page lists exactly
// that run (fast_api_voter/polity_fixtures/runs/explorer-fixture).

test.describe('Polity — run explorer', () => {
  test('opens the fixture run and shows its facts', async ({ page }) => {
    await page.goto('/polity');
    await expect(page.getByTestId('polity-page')).toBeVisible();

    const picker = page.getByTestId('polity-run-picker');
    await expect(picker.locator('option')).toHaveCount(1);
    await expect(picker.locator('option').first()).toHaveText(/^explorer-fixture — 40 /);

    await expect(page.getByTestId('polity-fact-population')).toContainText('40');
    await expect(page.getByTestId('polity-fact-duration')).toContainText('13');
    await expect(page.getByTestId('polity-fact-tick')).toContainText('1');
  });

  test('keeps the tick in the URL and clamps one past the run', async ({ page }) => {
    await page.goto('/polity?tick=9');
    // 9 ticks at 4 a year: year 3, quarter 2 — asserted on the numbers, not the words.
    await expect(page.getByTestId('polity-fact-tick')).toContainText(/3\D+2/);
    await page.goto('/polity?tick=999');
    await expect(page.getByTestId('polity-fact-tick')).toContainText(/4\D+1/);
  });
});
