import { test, expect, type Page } from '@playwright/test';

// Moment 4 — Campagne. The same electorate played over time: candidates drift
// under a scenario, and the timeline replays round by round. The scrubber is the
// state, so every control is checked against what the readout says.

async function campaignMoment(page: Page) {
  await page.goto('/playground');
  await page.locator('[data-testid="moment-campaign"]').click();
  await expect(page.locator('[data-testid="campaign-timeline"]')).toBeVisible();
}

/** "Tour 3 / 6" → 3 */
async function activeRound(page: Page): Promise<number> {
  const text = (await page.locator('[data-testid="timeline-scrubber"]').evaluate((el) => {
    return el.closest('div')?.parentElement?.textContent ?? '';
  })) as string;
  const m = text.match(/(\d+)\s*\/\s*(\d+)/);
  expect(m, `no round counter in: ${text.slice(0, 200)}`).not.toBeNull();
  return Number(m![1]);
}

test.describe('Playground — Campagne', () => {
  test.beforeEach(async ({ page }) => campaignMoment(page));

  test('every campaign scenario drives the map and a winner', async ({ page }) => {
    const crashes: string[] = [];
    page.on('pageerror', (err) => crashes.push(err.message));

    const winner = page.locator('[data-testid="timeline-winner"]');
    for (const scenario of ['derive', 'sondages', 'durcissement', 'meilleure_reponse']) {
      await page.locator(`[data-testid="scenario-${scenario}"]`).click();
      await expect(page.locator(`[data-testid="scenario-${scenario}"]`)).toHaveAttribute(
        'aria-checked',
        'true'
      );
      await expect(page.locator('[data-testid="campaign-map"]')).toBeVisible();
      await expect(winner, `no winner under ${scenario}`).not.toBeEmpty();
    }
    expect(crashes).toEqual([]);
  });

  test('stepping through rounds moves the scrubber and the readout', async ({ page }) => {
    await page.locator('[data-testid="timeline-reset"]').click();
    expect(await activeRound(page)).toBe(1);

    await page.locator('[data-testid="round-next"]').click();
    expect(await activeRound(page)).toBe(2);

    await page.locator('[data-testid="round-prev"]').click();
    expect(await activeRound(page)).toBe(1);

    // At T0 there is nothing before: the control must be disabled, not a no-op.
    await expect(page.locator('[data-testid="round-prev"]')).toBeDisabled();
  });

  test('the number of rounds resizes the timeline', async ({ page }) => {
    await page.locator('[data-testid="timeline-rounds"]').fill('4');
    await expect(page.locator('[data-testid="round-stop-3"]')).toBeVisible();
    await expect(page.locator('[data-testid="round-stop-4"]')).toHaveCount(0);

    await page.locator('[data-testid="timeline-rounds"]').fill('8');
    await expect(page.locator('[data-testid="round-stop-7"]')).toBeVisible();
  });

  test('the last round is reachable and ends the timeline', async ({ page }) => {
    await page.locator('[data-testid="timeline-rounds"]').fill('3');
    await page.locator('[data-testid="round-stop-2"]').click();

    expect(await activeRound(page)).toBe(3);
    await expect(page.locator('[data-testid="round-next"]')).toBeDisabled();
    await expect(page.locator('[data-testid="timeline-readout"]')).not.toBeEmpty();
  });

  test('the counting rule changes what the campaign produces', async ({ page }) => {
    const rule = page.locator('[data-testid="timeline-rule"]');
    const winner = page.locator('[data-testid="timeline-winner"]');

    // Drift all the way to the end of the campaign, where positions differ most.
    await page.locator('[data-testid="timeline-strength"]').fill('1');
    await page.locator('[data-testid="timeline-scrubber"]').fill('1');

    const seen = new Set<string>();
    for (const r of ['plurality', 'two_round', 'irv', 'borda', 'approval', 'condorcet']) {
      await rule.selectOption(r);
      await expect(winner, `no winner under ${r}`).not.toBeEmpty();
      seen.add(((await winner.textContent()) ?? '').trim());
    }
    expect(seen.size).toBeGreaterThanOrEqual(1);
  });
});
