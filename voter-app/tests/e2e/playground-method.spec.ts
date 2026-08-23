import { test, expect, type Page } from '@playwright/test';

// Moment 2 — Méthode. The rule selector, the multi-select of compared methods
// (which feeds the Bilan), the four lenses painted on the same map, and the
// step-by-step replay of a count.

async function methodMoment(page: Page) {
  await page.goto('/playground');
  await page.locator('[data-testid="moment-method"]').click();
  await expect(page.locator('[data-testid="moment-method-panel"]')).toBeVisible();
}

/** "12 / 29 méthodes actives" → [12, 29] */
async function enabledCount(page: Page): Promise<[number, number]> {
  const text = (await page.locator('[data-testid="moment-method-panel"]').textContent()) ?? '';
  const m = text.match(/(\d+)\s*\/\s*(\d+)\s*méthodes/);
  expect(m, `enabled-count label not found in: ${text.slice(0, 200)}`).not.toBeNull();
  return [Number(m![1]), Number(m![2])];
}

test.describe('Playground — Méthode', () => {
  test.beforeEach(async ({ page }) => methodMoment(page));

  test('the compared methods drive the Bilan table, one row per enabled rule', async ({ page }) => {
    await page.locator('[data-testid="rules-select-all"]').click();
    const [enabled, total] = await enabledCount(page);
    expect(enabled).toBe(total);

    await page.locator('[data-testid="moment-bilan"]').click();
    await page.locator('[data-testid="module-robustness-toggle"]').click();
    const rows = page.locator('[data-testid^="replay-row-"]');
    await expect(rows).toHaveCount(total);
  });

  test('unchecking a method removes it from the Bilan', async ({ page }) => {
    await page.locator('[data-testid="rules-select-all"]').click();
    const [before] = await enabledCount(page);

    await page.locator('[data-testid="rule-check-borda"]').click();
    const [after] = await enabledCount(page);
    expect(after).toBe(before - 1);

    await page.locator('[data-testid="moment-bilan"]').click();
    await page.locator('[data-testid="module-robustness-toggle"]').click();
    await expect(page.locator('[data-testid="replay-row-borda"]')).toHaveCount(0);
    await expect(page.locator('[data-testid="replay-row-plurality"]')).toBeVisible();
  });

  test('the compared set can never be emptied', async ({ page }) => {
    // Untick everything the panel offers; the engine must keep at least one rule,
    // otherwise the Bilan has nothing to conclude from.
    const checks = page.locator('[data-testid^="rule-check-"]');
    const n = await checks.count();
    for (let i = 0; i < n; i++) {
      const box = checks.nth(i).locator('input[type="checkbox"]');
      if (await box.isChecked()) await checks.nth(i).click();
    }
    const [left] = await enabledCount(page);
    expect(left).toBeGreaterThanOrEqual(1);

    await page.locator('[data-testid="moment-bilan"]').click();
    await expect(page.locator('[data-testid="bilan-verdict"]')).toBeVisible();
  });

  test('each rule keeps producing a winner', async ({ page }) => {
    const crashes: string[] = [];
    page.on('pageerror', (err) => crashes.push(err.message));

    const select = page.locator('[data-testid="rule-select"]');
    const winner = page.locator('[data-testid="field-winner"] strong').first();
    const values = await select
      .locator('option')
      .evaluateAll((os) => os.map((o) => (o as HTMLOptionElement).value));
    expect(values.length).toBeGreaterThan(10);

    for (const rule of values) {
      await select.selectOption(rule);
      await expect(winner, `no winner under ${rule}`).not.toBeEmpty();
    }
    expect(crashes).toEqual([]);
  });

  test('the four lenses each paint their own overlay', async ({ page }) => {
    const crashes: string[] = [];
    page.on('pageerror', (err) => crashes.push(err.message));

    const overlays: Record<string, string> = {
      winner: 'winregion',
      manipulation: 'manip-voters',
      probability: 'problens',
      criteria: 'criteria-matrix',
    };

    for (const [lens, overlay] of Object.entries(overlays)) {
      await page.locator(`[data-testid="lens-${lens}"]`).click();
      await expect(page.locator(`[data-testid="lens-${lens}"]`)).toHaveAttribute(
        'aria-checked',
        'true'
      );
      await expect(page.locator(`[data-testid="${overlay}"]`).first()).toBeAttached();
    }
    expect(crashes).toEqual([]);
  });

  test('the count can be replayed step by step', async ({ page }) => {
    await page.locator('[data-testid="replay-open"]').click();

    const method = page.locator('[data-testid="replay-method"]');
    await expect(method).toBeVisible();
    // The replay follows whichever method you point it at.
    await method.selectOption('irv');

    await page.locator('[data-testid="replay-speed-fast"]').click();
    await page.locator('[data-testid="replay-playpause"]').click();
    await page.locator('[data-testid="replay-restart"]').click();
    await expect(method).toBeVisible();

    await page.keyboard.press('Escape');
    await expect(method).toHaveCount(0);
  });
});
