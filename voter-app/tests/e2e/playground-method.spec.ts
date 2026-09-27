import { test, expect, type Page } from './coverageFixtures';

// Moment 2 — Méthode. The rule selector, the multi-select of compared methods
// (which feeds the Bilan), the four lenses painted on the same map, and the
// step-by-step replay of a count.

// The default electorate (DEFAULT_CONFIG in useElectionStore.tsx: Alice/Bob/Carol,
// seed 42, 300 voters, ideology 'random', 2-D) is what a fresh `/playground` load
// gets — Playwright gives each test an isolated context, so localStorage (which
// DOES persist the config, see useElectionStore.tsx's LS_KEY) starts empty. These
// are the real winners that exact electorate produces per rule (computed offline
// with the same sampleVoters/fieldWinnerName/LEADER_RULES this page calls —
// PLAN_SURFACE_EXTERIEURE.md §2.F). A result oracle, not a re-proof: correctness
// of each rule is already covered by unit tests and the client⇄backend parity
// harness; this only catches the UI/wiring layer returning the WRONG (but
// non-empty) answer, which `not.toBeEmpty()` alone could never catch — a rule
// dispatch bug or a stale/disconnected `winner` computation would still pass it.
// Regenerate by running LEADER_RULES through fieldWinnerName(sampleVoters(300, 42,
// 'random', 2), DEFAULT_CONFIG.candidates, rule) if the default electorate or a
// rule's algorithm changes.
const EXPECTED_WINNER: Record<string, string> = {
  plurality: 'Alice',
  two_round: 'Carol',
  irv: 'Carol',
  borda: 'Carol',
  approval: 'Carol',
  score: 'Carol',
  star: 'Carol',
  majority_judgment: 'Carol',
  cumulative: 'Carol',
  maximin: 'Alice',
  nash: 'Carol',
  bucklin: 'Carol',
  coombs: 'Carol',
  condorcet: 'Carol',
  minimax: 'Carol',
  schulze: 'Carol',
  nanson: 'Carol',
  baldwin: 'Carol',
  ranked_pairs: 'Carol',
  kemeny: 'Carol',
  black: 'Carol',
  anti_plurality: 'Carol',
  dowdall: 'Carol',
  raynaud: 'Carol',
  benham: 'Carol',
  river: 'Carol',
  smith_irv: 'Carol',
  split_cycle: 'Carol',
  random_ballot: 'Alice',
};

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

  test('the compared set can never be emptied', async ({ page, browserName }) => {
    // WebKit-only: this loop drives ~28 real, sequential clicks, and a clean
    // (uncontended) CI run measured WebKit at ~30.8s for that -- against
    // this suite's 30s per-test ceiling, essentially zero margin, not a
    // render-storm bug. Chromium/Firefox run the identical interaction in
    // ~4-6s (flake investigation, 2026-09-14, after the PlaygroundController
    // context-split fix, PR #465, closed a real but separate re-render
    // coupling that WAS the original cause of this test's earlier flakes).
    // Budget for WebKit's real per-action cost instead of leaving a test at
    // ~100% of its own timeout.
    test.slow(browserName === 'webkit', 'WebKit needs ~30s for this loop of 28 real clicks alone');

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

  test('each rule elects its known winner on the default electorate', async ({ page }) => {
    const crashes: string[] = [];
    page.on('pageerror', (err) => crashes.push(err.message));

    const select = page.locator('[data-testid="rule-select"]');
    const winner = page.locator('[data-testid="field-winner"] strong').first();
    const values = await select
      .locator('option')
      .evaluateAll((os) => os.map((o) => (o as HTMLOptionElement).value));
    expect(values.length).toBeGreaterThan(10);
    // Every rule the select offers must have a known expected winner recorded
    // above — an unlisted rule would silently fall back to `not.toBeEmpty()`
    // rigour, exactly the gap this test closes.
    expect(values.every((r) => r in EXPECTED_WINNER)).toBe(true);

    for (const rule of values) {
      await select.selectOption(rule);
      await expect(winner, `wrong winner under ${rule}`).toHaveText(EXPECTED_WINNER[rule]);
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

  test('a lens click survives the robustness strip landing mid-click', async ({ page }) => {
    // The strip above the lens switch fills in on a timer after the moment opens.
    // It once pushed the switch down between a click's press and release, so the
    // release missed the button (the Firefox flake of the test above). Hold the
    // timer, press, let the strip land, release: the lens must still be selected.
    await page.clock.install({ time: new Date('2026-01-01T08:00:00') });
    await page.goto('/playground');
    await expect(page.locator('[data-testid="moment-method"]')).toBeVisible();
    await page.clock.pauseAt(new Date('2026-01-01T09:00:00'));

    await page.locator('[data-testid="moment-method"]').click();
    await expect(page.locator('[data-testid="winner-robustness-pending"]')).toBeAttached();
    const lens = page.locator('[data-testid="lens-winner"]');
    await expect(lens).toHaveAttribute('aria-checked', 'false');
    const box = await lens.boundingBox();
    expect(box).not.toBeNull();
    await page.mouse.move(box!.x + box!.width / 2, box!.y + box!.height / 2);
    await page.mouse.down();

    await page.clock.runFor(1_000);
    await expect(page.locator('[data-testid="winner-robustness"]')).toBeVisible();
    await page.mouse.up();
    await expect(lens).toHaveAttribute('aria-checked', 'true');
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
