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

  test('the player scrubs, steps and plays to the end of the run', async ({ page }) => {
    await page.goto('/polity');
    const tick = () => new URL(page.url()).searchParams.get('tick');

    await page.getByTestId('player-slider').fill('9');
    await expect.poll(tick).toBe('9');
    await page.getByTestId('player-step-forward').click();
    await expect.poll(tick).toBe('10');

    await page.getByTestId('player-speed').selectOption('8');
    await page.getByTestId('player-toggle').click();
    await expect.poll(tick).toBe('12');
    await expect(page.getByTestId('player-toggle')).toHaveAttribute('aria-pressed', 'false');
  });

  test('the timeline shows the fixture run’s recalls and jumps to them', async ({ page }) => {
    await page.goto('/polity');
    const timeline = page.getByTestId('polity-timeline');
    await expect(
      timeline.locator('[data-testid="timeline-glyph"][data-kind="recall"]')
    ).toHaveCount(2);
    await expect(timeline.getByTestId('timeline-term')).toHaveCount(3);

    await timeline.locator('details > summary').click();
    await timeline
      .locator('[data-testid="timeline-event-jump"][data-event="recalled"][data-tick="11"]')
      .click();
    await expect.poll(() => new URL(page.url()).searchParams.get('tick')).toBe('11');
  });

  test('the map follows the player, switches lenses and selects a citizen', async ({ page }) => {
    const param = (name: string) => new URL(page.url()).searchParams.get(name);
    // Tick 10 of the fixture run holds an election: 40 ballots, one of them blank.
    await page.goto('/polity?tick=10&lens=vote');
    await expect(page.getByTestId('polity-map-canvas')).toBeVisible();
    await expect(page.getByTestId('polity-legend-blank')).toContainText('1');
    await expect(page.getByTestId('polity-legend-forWinner')).toBeVisible();

    await page.getByTestId('polity-lens-act').click();
    await expect.poll(() => param('lens')).toBe('act');
    await expect(page.getByTestId('polity-lens-act')).toHaveAttribute('aria-checked', 'true');

    await page.getByTestId('polity-table').locator('summary').click();
    await page.getByTestId('polity-row-3').getByRole('button').click();
    await expect.poll(() => param('citizen')).toBe('3');
    await expect(page.getByTestId('polity-map-selection')).toBeVisible();

    await page.getByTestId('polity-map-surface').focus();
    await page.keyboard.press('Escape');
    await expect.poll(() => param('citizen')).toBeNull();
    await page.keyboard.press('ArrowUp');
    await expect.poll(() => param('citizen')).not.toBeNull();
  });

  test('the curves panel opens on demand and lists the fixture run’s elections', async ({
    page,
  }) => {
    await page.goto('/polity');
    await expect(page.getByTestId('polity-macro-panel')).toHaveCount(0);
    await page.getByTestId('polity-macro-toggle').click();
    await expect(page.getByTestId('polity-macro-panel')).toBeVisible();
    for (const tick of [0, 10, 12]) {
      await expect(page.getByTestId(`polity-election-${tick}`)).toBeVisible();
    }
    await page.getByTestId('polity-election-10').getByRole('button').click();
    await expect.poll(() => new URL(page.url()).searchParams.get('tick')).toBe('10');
  });

  test('a citizen’s biography opens from the map’s table and moves the player', async ({
    page,
  }) => {
    // Citizen 3 of the fixture run takes a pressure act at nearly every tick.
    await page.goto('/polity');
    await expect(page.getByTestId('polity-biography')).toHaveCount(0);
    await page.getByTestId('polity-table').locator('summary').click();
    await page.getByTestId('polity-row-3').getByRole('button').click();

    const biography = page.getByTestId('polity-biography');
    await expect(biography).toBeVisible();
    const acts = biography
      .getByTestId('biography-section-pressure_acts')
      .getByTestId('biography-entry');
    await expect(acts.first()).toBeVisible();
    expect(await acts.count()).toBeGreaterThan(5);

    await acts.nth(2).getByTestId('biography-tick').click();
    await expect.poll(() => new URL(page.url()).searchParams.get('tick')).not.toBeNull();
    await biography.getByTestId('polity-biography-close').click();
    await expect.poll(() => new URL(page.url()).searchParams.get('citizen')).toBeNull();
  });
});
