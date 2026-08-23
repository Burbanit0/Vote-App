import { test, expect, type Page } from '@playwright/test';

// Moment 3 — Stratégie. Tactical voting (who defects and does it pay), blank
// votes under four legal regimes, and turnout models. These are the knobs that
// change WHO the ballots come from, so the assertions here are about the numbers
// the panel prints, not just about elements existing.

async function strategyMoment(page: Page) {
  await page.goto('/playground');
  await page.locator('[data-testid="moment-strategy"]').click();
  await expect(page.locator('[data-testid="moment-strategy-panel"]')).toBeVisible();
}

/** "Taux de participation : 87 % (52 abstentions)" → 87 */
async function turnoutPct(page: Page): Promise<number> {
  const text = (await page.locator('[data-testid="turnout-rate"]').textContent()) ?? '';
  const m = text.match(/(\d+)\s*%/);
  expect(m, `no turnout percentage in: ${text}`).not.toBeNull();
  return Number(m![1]);
}

test.describe('Playground — Stratégie', () => {
  test.beforeEach(async ({ page }) => strategyMoment(page));

  test('"Vous" appear on the map for this moment only', async ({ page }) => {
    await expect(page.locator('[data-testid="you-marker"]')).toBeVisible();
    await page.locator('[data-testid="moment-method"]').click();
    await expect(page.locator('[data-testid="you-marker"]')).toHaveCount(0);
  });

  test('a strategic electorate exposes the tactic panel and an outcome', async ({ page }) => {
    // Sincere voters have no tactic to choose.
    await expect(page.locator('[data-testid="tactic-panel"]')).toHaveCount(0);

    await page.locator('#pg-behavior').selectOption('strategic');
    await expect(page.locator('[data-testid="tactic-panel"]')).toBeVisible();

    const outcome = page.locator('[data-testid="strategic-outcome"]');
    await expect(outcome).toBeVisible();

    // Both tactics must produce a readable verdict — burying used to be the
    // untested branch of the pair.
    for (const tactic of ['compromise', 'burying']) {
      await page.locator('[data-testid="tactic-select"]').selectOption(tactic);
      await expect(outcome).not.toBeEmpty();
    }

    // A bigger defecting bloc keeps the readout consistent, never blank.
    await page.locator('[data-testid="coalition-share"]').fill('0.5');
    await expect(outcome).not.toBeEmpty();
  });

  test('turnout never rises when abstention bites harder', async ({ page }) => {
    await page.locator('[data-testid="turnout-select"]').selectOption('alienation');
    const intensity = page.locator('[data-testid="turnout-intensity"]');

    await intensity.fill('0');
    const atZero = await turnoutPct(page);
    expect(atZero).toBeLessThanOrEqual(100);

    await intensity.fill('1');
    const atMax = await turnoutPct(page);

    // Monotonic by construction: more alienation can only remove voters.
    expect(atMax).toBeLessThanOrEqual(atZero);
    expect(atMax).toBeGreaterThanOrEqual(0);
  });

  test('every abstention model computes a turnout', async ({ page }) => {
    for (const model of ['indifference', 'alienation']) {
      await page.locator('[data-testid="turnout-select"]').selectOption(model);
      await page.locator('[data-testid="turnout-intensity"]').fill('0.5');
      const pct = await turnoutPct(page);
      expect(pct, `turnout out of range under ${model}`).toBeGreaterThanOrEqual(0);
      expect(pct).toBeLessThanOrEqual(100);
    }

    // Back to full participation: the readout disappears, nobody abstains.
    await page.locator('[data-testid="turnout-select"]').selectOption('full');
    await expect(page.locator('[data-testid="turnout-rate"]')).toHaveCount(0);
  });

  test('blank votes are counted under each legal regime', async ({ page }) => {
    await page.locator('[data-testid="blank-toggle"]').check();
    await page.locator('[data-testid="blank-intensity"]').fill('0.6');

    const rate = page.locator('[data-testid="blank-rate"]');
    await expect(rate).toContainText('%');

    const lens = page.locator('[data-testid="blank-lens-select"]');
    const regimes = await lens
      .locator('option')
      .evaluateAll((os) => os.map((o) => (o as HTMLOptionElement).value));
    expect(regimes.length).toBeGreaterThanOrEqual(4);

    for (const regime of regimes) {
      await lens.selectOption(regime);
      // Each regime must state what it does with the blank ballots.
      await expect(page.locator('[data-testid="blank-verdict"]'), regime).not.toBeEmpty();
    }
  });

  test('the strategic-vulnerability module runs and lists methods', async ({ page }) => {
    await page.locator('[data-testid="module-strategic-toggle"]').click();
    await page.locator('[data-testid="strategic-run"]').click();
    await expect(page.locator('[data-testid="strategic-rows"]')).toBeVisible({ timeout: 30_000 });
    await expect(page.locator('[data-testid="strategic-rows"]')).not.toBeEmpty();
  });
});
