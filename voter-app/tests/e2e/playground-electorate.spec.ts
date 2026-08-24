import { test, expect, type Page } from '@playwright/test';

// Moment 1 — Électorat. The knobs that define WHO votes: presets, sample size,
// seed, composition (communities), and the advanced space/source settings.
// The instrument's status strip is the observable: it prints candidates, voters,
// rule and seed, so a knob that does not reach the engine shows up here.

const status = (page: Page) => page.locator('[data-testid="playground-page"]');

/** The composer is a Collapsible: it re-collapses whenever the panel remounts. */
async function openComposer(page: Page) {
  const seed = page.locator('[data-testid="electorate-seed"]');
  if (!(await seed.isVisible())) {
    await page.locator('[data-testid="module-electorate-toggle"]').click();
    await expect(seed).toBeVisible();
  }
}

/** Read the winner — only visible from moment 2 on, so hop there and back. */
async function winnerFromMethodMoment(page: Page): Promise<string> {
  await page.locator('[data-testid="moment-method"]').click();
  const winner = page.locator('[data-testid="field-winner"] strong').first();
  await expect(winner).not.toBeEmpty();
  const name = ((await winner.textContent()) ?? '').trim();
  await page.locator('[data-testid="moment-electorate"]').click();
  return name;
}

test.describe('Playground — Électorat', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/playground');
    await expect(page.locator('[data-testid="moment-electorate-panel"]')).toBeVisible();
  });

  test('every start preset loads and reaches the instrument', async ({ page }) => {
    const crashes: string[] = [];
    page.on('pageerror', (err) => crashes.push(err.message));

    // Preset data from useElectionStore: the sample size is echoed by the status
    // strip, and two presets are assembly scenarios — they must flip the mode
    // switch and swap the instrument, not just repaint the map.
    const expected: [preset: string, voters: number, mode: 'leader' | 'parliament'][] = [
      ['two_party', 400, 'leader'],
      ['fragmented', 600, 'parliament'],
      ['single_issue', 300, 'leader'],
      ['france2002_like', 500, 'leader'],
      ['usa2000_like', 400, 'leader'],
      ['weimar1932_like', 600, 'parliament'],
    ];

    for (const [preset, voters, mode] of expected) {
      await page.locator(`[data-testid="preset-${preset}"]`).click();
      await expect(status(page)).toContainText(new RegExp(`${voters}\\s*électeurs`));
      await expect(page.locator(`[data-testid="mode-toggle-${mode}"]`)).toHaveAttribute(
        'aria-checked',
        'true'
      );
      const canvas = mode === 'leader' ? 'leader-canvas' : 'canvas-parliament';
      await expect(page.locator(`[data-testid="${canvas}"]`)).toBeVisible();
    }
    expect(crashes).toEqual([]);
  });

  test('the seed reaches the engine and the same seed gives the same winner', async ({ page }) => {
    await openComposer(page);
    const seed = page.locator('[data-testid="electorate-seed"]');

    await seed.fill('4242');
    await expect(status(page)).toContainText('seed 4242');
    const first = await winnerFromMethodMoment(page);

    await openComposer(page);
    await seed.fill('777');
    await expect(status(page)).toContainText('seed 777');
    await winnerFromMethodMoment(page);

    // Determinism: the electorate is a pure function of the seed.
    await openComposer(page);
    await seed.fill('4242');
    expect(await winnerFromMethodMoment(page)).toBe(first);
  });

  test('rerolling the seed changes it', async ({ page }) => {
    await openComposer(page);
    const seed = page.locator('[data-testid="electorate-seed"]');
    await seed.fill('1');
    await page.locator('[data-testid="electorate-seed-reroll"]').click();
    await expect(seed).not.toHaveValue('1');
  });

  test('the sample size slider drives the electorate', async ({ page }) => {
    await openComposer(page);
    await page.locator('[data-testid="electorate-num-voters"]').fill('150');
    await expect(status(page)).toContainText('150');
  });

  test('composed mode exposes communities and can add one', async ({ page }) => {
    await openComposer(page);
    await page.locator('[data-testid="electorate-mode-composed"]').click();

    const list = page.locator('[data-testid="community-list"]');
    await expect(list).toBeVisible();
    // One remove button per community — the unambiguous row count.
    const rows = list.locator('[data-testid^="community-remove-"]');
    const before = await rows.count();
    expect(before).toBeGreaterThan(0);

    await page.locator('[data-testid="community-add"]').click();
    await expect(rows).toHaveCount(before + 1);

    // The composed electorate still renders on the instrument.
    await expect(page.locator('[data-testid="leader-canvas"]')).toBeVisible();
  });

  test('a composition exports to JSON and imports back; bad JSON is rejected', async ({ page }) => {
    await openComposer(page);
    await page.locator('[data-testid="electorate-mode-composed"]').click();
    await page.locator('[data-testid="electorate-io"] summary').click();

    await page.locator('[data-testid="electorate-export"]').click();
    const json = page.locator('[data-testid="electorate-json"]');
    await expect(json).not.toBeEmpty();
    const exported = (await json.inputValue()).trim();
    expect(() => JSON.parse(exported)).not.toThrow();

    // Re-importing what we just exported must be accepted…
    await page.locator('[data-testid="electorate-import"]').click();
    await expect(page.locator('[data-testid="electorate-json-error"]')).toHaveCount(0);

    // …and garbage must be refused, not swallowed.
    await json.fill('{ not json');
    await page.locator('[data-testid="electorate-import"]').click();
    await expect(page.locator('[data-testid="electorate-json-error"]')).toBeVisible();
  });

  test('the space can be switched to 1-D and 3-D', async ({ page }) => {
    await page.locator('[data-testid="electorate-advanced-toggle"]').click();
    const dims = page.locator('#pg-dims');

    await dims.selectOption('3');
    await expect(page.locator('[data-testid="leader-canvas"]')).toHaveAttribute('data-dims', '3');

    await dims.selectOption('1');
    await expect(page.locator('[data-testid="leader-canvas"]')).toHaveAttribute('data-dims', '1');
  });

  test('a non-spatial preference source swaps the map and says so', async ({ page }) => {
    await page.locator('[data-testid="electorate-advanced-toggle"]').click();
    await page.locator('#pg-source').selectOption('mallows');

    await expect(page.locator('[data-testid="nonspatial-note"]')).toBeVisible();
    // The spatial canvas is replaced by the profile map — never both.
    await expect(page.locator('[data-testid="leader-canvas"]')).toHaveCount(0);
  });
});
