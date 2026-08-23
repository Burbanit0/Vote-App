import { test, expect, type Page } from '@playwright/test';

// Assemblée mode. Unlike the leader canvas, the numbers here come from the
// backend (/assembly): seats, Gallagher, effective parties, wasted votes. These
// tests cross-check the rendered hemicycle against those numbers — the frontend
// draws the seats itself, so a drift between the two is invisible to unit tests
// on either side.

async function assemblyMode(page: Page) {
  await page.goto('/playground');
  await page.locator('[data-testid="mode-toggle-parliament"]').click();
  await expect(page.locator('[data-testid="canvas-parliament"]')).toBeVisible();
  // Wait for the first backend result — everything below depends on it.
  await expect(page.locator('[data-testid="votes-seats-bars"]')).toBeVisible({ timeout: 30_000 });
}

/** "100 sièges · majorité 51" → { seats: 100, majority: 51 } */
async function seatsLine(page: Page): Promise<{ seats: number; majority: number }> {
  const text = (await page.locator('[data-testid="canvas-parliament"] svg text').allTextContents())
    .join(' ')
    .replace(/\s+/g, ' ');
  const m = text.match(/(\d+)\s*sièges\s*·\s*majorité\s*(\d+)/);
  expect(m, `no seats line in: ${text.slice(0, 200)}`).not.toBeNull();
  return { seats: Number(m![1]), majority: Number(m![2]) };
}

test.describe('Assemblée — hemicycle, seats and coalitions', () => {
  test.beforeEach(async ({ page }) => assemblyMode(page));

  test('the hemicycle draws exactly the seats the backend allocated', async ({ page }) => {
    const { seats, majority } = await seatsLine(page);
    expect(seats).toBeGreaterThan(0);
    // A majority is strictly more than half the chamber.
    expect(majority).toBeGreaterThan(seats / 2);
    expect(majority).toBeLessThanOrEqual(seats);

    const drawn = page.locator('[data-testid="hemicycle"] circle');
    await expect(drawn).toHaveCount(seats);
  });

  test('a coalition of every party holds the whole chamber', async ({ page }) => {
    const status = page.locator('[data-testid="coalition-status"]');
    await expect(status).toBeVisible();

    const parties = page.locator('[data-testid^="coalition-toggle-"]');
    const n = await parties.count();
    expect(n).toBeGreaterThan(1);
    for (let i = 0; i < n; i++) await parties.nth(i).click();

    const { seats } = await seatsLine(page);
    // Everyone in ⇒ every seat is in, and that is by definition a majority.
    await expect(status).toContainText(String(seats));
    await expect(status).toContainText('majorité');
  });

  test('the chamber size is a knob, and the drawing follows it', async ({ page }) => {
    await page.locator('[data-testid="moment-method"]').click();
    await page.locator('#pg-seats').fill('200');

    await expect.poll(async () => (await seatsLine(page)).seats, { timeout: 30_000 }).toBe(200);
    await expect(page.locator('[data-testid="hemicycle"] circle')).toHaveCount(200);
  });

  test('every electoral structure returns an allocation', async ({ page }) => {
    const crashes: string[] = [];
    page.on('pageerror', (err) => crashes.push(err.message));

    await page.locator('[data-testid="moment-method"]').click();
    for (const structure of ['pr', 'fptp', 'mmp']) {
      await page.locator('#pg-structure').selectOption(structure);
      await expect(page.locator('[data-testid="assembly-metrics"]'), structure).toBeVisible({
        timeout: 30_000,
      });
      const { seats } = await seatsLine(page);
      expect(seats, `no seats under ${structure}`).toBeGreaterThan(0);
      await expect(page.locator('[data-testid="hemicycle"] circle')).toHaveCount(seats);
    }
    expect(crashes).toEqual([]);
  });

  test('the assembly Bilan names the structure it was computed with', async ({ page }) => {
    await page.locator('[data-testid="moment-method"]').click();
    await page.locator('#pg-structure').selectOption('mmp');

    await page.locator('[data-testid="moment-bilan"]').click();
    const bilan = page.locator('[data-testid="moment-bilan-panel"]');
    await expect(bilan).toContainText('Évalué pour');
    await expect(bilan).toContainText('MMP');
  });
});
