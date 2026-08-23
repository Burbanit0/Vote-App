import { test, expect } from '@playwright/test';

// The playground is a single instrument: a Dirigeant/Assemblée switch above a
// rail of five moments (Électorat → Méthode → Stratégie → Campagne → Bilan).
// The winner is computed client-side (playgroundVoting.ts) except in Assemblée
// mode, where seats come from the backend /assembly endpoint — that one test is
// the reason the e2e job boots uvicorn.

test.describe('HomePage hero — the thesis, live', () => {
  test('switching the counting rule changes the winner on the same ballots', async ({ page }) => {
    await page.goto('/');
    const winner = page.locator('[data-testid="hero-winner"]');
    const seen = new Set<string>();

    for (const rule of ['plurality', 'runoff', 'approval']) {
      await page.locator(`[data-testid="hero-rule-${rule}"]`).click();
      await expect(winner).not.toBeEmpty();
      seen.add(((await winner.textContent()) ?? '').trim());
    }

    // The whole point of the landing instrument: same electorate, different rule,
    // different laureate. One winner for all three rules means it is broken.
    expect(seen.size).toBeGreaterThan(1);
  });
});

test.describe('Playground — the instrument', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/playground');
    await expect(page.locator('[data-testid="playground-page"]')).toBeVisible();
  });

  test('the moment rail swaps the control panel', async ({ page }) => {
    // Moment 1 is the default.
    await expect(page.locator('[data-testid="moment-electorate-panel"]')).toBeVisible();

    for (const moment of ['method', 'strategy', 'bilan']) {
      await page.locator(`[data-testid="moment-${moment}"]`).click();
      await expect(page.locator(`[data-testid="moment-${moment}-panel"]`)).toBeVisible();
    }
  });

  test('the rule selector appears from the Méthode moment and feeds the winner readout', async ({
    page,
  }) => {
    // Moment 1 deliberately hides the rule UI — the electorate comes first.
    await expect(page.locator('[data-testid="rule-select"]')).toHaveCount(0);

    await page.locator('[data-testid="moment-method"]').click();
    const select = page.locator('[data-testid="rule-select"]');
    await expect(select).toBeVisible();

    const winner = page.locator('[data-testid="field-winner"] strong').first();
    await expect(winner).not.toBeEmpty();

    await select.selectOption('borda');
    await expect(select).toHaveValue('borda');
    await expect(winner).not.toBeEmpty();
  });

  test('the Bilan moment reports which methods elect whom', async ({ page }) => {
    await page.locator('[data-testid="moment-bilan"]').click();
    await expect(page.locator('[data-testid="bilan-verdict"]')).toBeVisible();
    // At least one laureate group — every enabled method is attributed to someone.
    await expect(page.locator('[data-testid^="winner-group-"]').first()).toBeVisible();
  });

  test('the Dirigeant/Assemblée switch swaps the instrument (backend-backed)', async ({ page }) => {
    await expect(page.locator('[data-testid="leader-canvas"]')).toBeVisible();

    await page.locator('[data-testid="mode-toggle-parliament"]').click();
    await expect(page.locator('[data-testid="mode-toggle-parliament"]')).toHaveAttribute(
      'aria-checked',
      'true'
    );
    // Seats come from the backend — this fails if /assembly is down or broken.
    await expect(page.locator('[data-testid="votes-seats-bars"]')).toBeVisible({ timeout: 30_000 });

    await page.locator('[data-testid="mode-toggle-leader"]').click();
    await expect(page.locator('[data-testid="leader-canvas"]')).toBeVisible();
  });
});
