import { test, expect, type Page } from './coverageFixtures';

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

  test('candidates can be added, renamed and removed, and the instrument follows', async ({
    page,
  }) => {
    const crashes: string[] = [];
    page.on('pageerror', (err) => crashes.push(err.message));

    // Closed at first paint (the form-lock); one click, and the three candidates are listed.
    // (Anchored on test ids: these tests run in French.)
    await expect(page.locator('[data-testid="candidate-editor"]')).toHaveCount(0);
    await page.locator('[data-testid="module-candidates-toggle"]').click();
    await expect(page.locator('[data-testid="candidate-row-2"]')).toBeVisible();
    await expect(page.locator('[data-testid="candidate-row-3"]')).toHaveCount(0);

    // Add: a fourth row, and a fourth handle on the map.
    await page.locator('[data-testid="candidate-add"]').click();
    await expect(page.locator('[data-testid="candidate-row-3"]')).toBeVisible();
    await expect(page.locator('[data-testid="candidate-3"]')).toBeVisible();

    // Rename (Enter commits): the map labels the candidate with the new name.
    const name = page.locator('[data-testid="candidate-name-3"]');
    await name.fill('Zed');
    await name.press('Enter');
    await expect(page.locator('[data-testid="leader-map"]')).toContainText('Zed');

    // A name another candidate has is refused, and Escape takes it back.
    await name.fill('Alice');
    await expect(page.getByRole('alert')).toBeVisible();
    await name.press('Escape');
    await expect(name).toHaveValue('Zed');

    // Remove: back to three, and the handle is gone.
    await page.locator('[data-testid="candidate-remove-3"]').click();
    await expect(page.locator('[data-testid="candidate-row-3"]')).toHaveCount(0);
    await expect(page.locator('[data-testid="candidate-3"]')).toHaveCount(0);

    // The instrument still elects someone with the edited field.
    expect(await winnerFromMethodMoment(page)).not.toBe('');
    expect(crashes).toEqual([]);
  });

  test('a double-click on an empty spot of the map adds an entrant; on a candidate it does not', async ({
    page,
  }) => {
    const crashes: string[] = [];
    page.on('pageerror', (err) => crashes.push(err.message));

    await page.locator('[data-testid="module-candidates-toggle"]').click();
    await expect(page.locator('[data-testid="candidate-row-2"]')).toBeVisible();
    await expect(page.locator('[data-testid="candidate-row-3"]')).toHaveCount(0);

    // A spot inside the map, off the three candidates (a locator click: it scrolls the map into
    // view and checks the point is reachable, which a raw page.mouse event does not).
    const map = page.locator('[data-testid="leader-map"]');
    const box = (await map.boundingBox())!;
    await map.dblclick({ position: { x: box.width * 0.72, y: box.height * 0.2 } });

    // A fourth row, and a fourth handle on the map, under the pointer. (This test runs at 720 px
    // of viewport height, where the map is letterboxed: it used to land 19 px to the left.)
    await expect(page.locator('[data-testid="candidate-row-3"]')).toBeVisible();
    const dot = page.locator('[data-testid="candidate-3"] circle').first();
    const at = (await dot.boundingBox())!;
    // Where the click was, now (the click may have scrolled the map into view).
    const now = (await map.boundingBox())!;
    expect([now.width, now.height]).toEqual([box.width, box.height]); // the click moved nothing
    const spot = { x: now.x + box.width * 0.72, y: now.y + box.height * 0.2 };
    expect(Math.hypot(at.x + at.width / 2 - spot.x, at.y + at.height / 2 - spot.y)).toBeLessThan(
      2.5
    );

    // A double-click on a candidate is the candidate's, not the ground's: no fifth entrant. Let
    // the frames after the click land first, or "nothing appeared" is true of a handler that has
    // not run yet.
    await page.locator('[data-testid="candidate-0"]').dblclick();
    await page.evaluate(
      () =>
        new Promise<void>((done) =>
          requestAnimationFrame(() => requestAnimationFrame(() => done()))
        )
    );
    await expect(page.locator('[data-testid="candidate-row-4"]')).toHaveCount(0);
    expect(crashes).toEqual([]);
  });

  // The map is a square drawing in a box capped at 52vh tall: on a short viewport the box is wider
  // than the drawing and leaves a margin each side, which the pointer used to count as map (the
  // handle landed 26 px from the pointer at 720 px, 44 px at 600, and exactly under it at 1000).
  for (const height of [600, 720, 1000]) {
    test(`a dragged candidate lands under the pointer, at ${height} px of viewport height`, async ({
      page,
    }) => {
      await page.setViewportSize({ width: 1280, height });
      const map = page.locator('[data-testid="leader-map"]');
      await map.scrollIntoViewIfNeeded();
      // The resize re-lays the map out: let it settle before reading where the handle is.
      await page.evaluate(
        () =>
          new Promise<void>((done) =>
            requestAnimationFrame(() => requestAnimationFrame(() => done()))
          )
      );
      const dot = page.locator('[data-testid="candidate-0"] circle').first();
      const centre = async () => {
        const b = (await dot.boundingBox())!;
        return { x: b.x + b.width / 2, y: b.y + b.height / 2 };
      };
      const from = await centre();
      const drag = async (a: { x: number; y: number }, b: { x: number; y: number }) => {
        await page.mouse.move(a.x, a.y);
        await page.mouse.down();
        await page.mouse.move(b.x, b.y, { steps: 6 });
        await page.mouse.up();
      };
      const distanceTo = (p: { x: number; y: number }) => async () => {
        const at = await centre();
        return Math.hypot(at.x - p.x, at.y - p.y);
      };
      // Two stretches, left of where it started and right of it, and back each time.
      const left = { x: from.x - 40, y: from.y };
      const right = { x: from.x + 120, y: from.y };
      // Relative to where the handle starts, so they stay inside the plot (a target in the map's
      // margin would be clamped to its edge) at every height; and real stretches, so the test
      // cannot pass by the handle staying put.
      expect(from.x - left.x).toBeGreaterThan(20);
      expect(right.x - from.x).toBeGreaterThan(20);
      await drag(from, left);
      await expect.poll(distanceTo(left)).toBeLessThan(2.5);
      await drag(left, from);
      await expect.poll(distanceTo(from)).toBeLessThan(2.5);
      await drag(from, right);
      await expect.poll(distanceTo(right)).toBeLessThan(2.5);
    });
  }

  test('a name typed and left with a click elsewhere is kept (no Enter needed)', async ({
    page,
  }) => {
    await page.locator('[data-testid="module-candidates-toggle"]').click();
    await page.locator('[data-testid="candidate-name-0"]').fill('Zed');
    // Leave by clicking another moment: the field blurs first, which commits the name.
    await page.locator('[data-testid="moment-method"]').click();
    await page.locator('[data-testid="moment-electorate"]').click();
    await page.locator('[data-testid="module-candidates-toggle"]').click();
    await expect(page.locator('[data-testid="candidate-name-0"]')).toHaveValue('Zed');
  });
});
