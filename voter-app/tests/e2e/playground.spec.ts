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

  test('the guided footer walks the five moments in order', async ({ page }) => {
    const order = ['electorate', 'method', 'strategy', 'campaign', 'bilan'];

    for (let i = 1; i < order.length; i++) {
      await page.locator('[data-testid="guided-next"]').click();
      await expect(page.locator(`[data-testid="moment-${order[i]}"]`)).toHaveAttribute(
        'aria-checked',
        'true'
      );
    }
    // At the end the same control loops back to moment 1 rather than dead-ending.
    await page.locator('[data-testid="guided-next"]').click();
    await expect(page.locator('[data-testid="moment-electorate"]')).toHaveAttribute(
      'aria-checked',
      'true'
    );
    await expect(page.locator('[data-testid="guided-prev"]')).toBeDisabled();

    await page.locator('[data-testid="moment-bilan"]').click();
    await page.locator('[data-testid="guided-prev"]').click();
    await expect(page.locator('[data-testid="moment-campaign"]')).toHaveAttribute(
      'aria-checked',
      'true'
    );
  });

  test('a story runs on the instrument, step by step, and can be quit', async ({ page }) => {
    const crashes: string[] = [];
    page.on('pageerror', (err) => crashes.push(err.message));

    await page.locator('[data-testid="story-launch"]').click();
    await expect(page.locator('[data-testid="story-picker"]')).toBeVisible();
    await page.locator('[data-testid="story-pick-spoiler"]').click();

    const beat = page.locator('[data-testid="story-beat"]');
    await expect(page.locator('[data-testid="story-bar"]')).toBeVisible();
    await expect(beat).not.toBeEmpty();

    // Each step must actually say something new about the same instrument.
    const first = (await beat.textContent()) ?? '';
    await page.locator('[data-testid="story-next"]').click();
    await expect(beat).not.toHaveText(first);

    // Walk to the end — "restart" only exists on the last step.
    const next = page.locator('[data-testid="story-next"]');
    for (let i = 0; (await next.count()) > 0 && i < 20; i++) await next.click();
    await expect(page.locator('[data-testid="story-restart"]')).toBeVisible();

    await page.locator('[data-testid="story-restart"]').click();
    await expect(beat).toHaveText(first);

    await page.locator('[data-testid="story-quit"]').click();
    await expect(page.locator('[data-testid="story-bar"]')).toHaveCount(0);
    expect(crashes).toEqual([]);
  });

  test('a story can be deep-linked from the URL', async ({ page }) => {
    await page.goto('/playground?story=squeeze');
    await expect(page.locator('[data-testid="story-bar"]')).toBeVisible();
    await expect(page.locator('[data-testid="story-beat"]')).not.toBeEmpty();
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
