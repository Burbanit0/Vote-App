import { test, expect, type Page } from '@playwright/test';

// The Laboratoire is a rail of six families → a catalogue of ~57 fiches → one
// full-width bench. Every fiche is a lazily-loaded module, so the sweep below is
// the only place that actually mounts all of them: it is what catches a fiche
// that throws, never resolves, or renders nothing.

const FAMILIES = ['methods', 'rules', 'systems', 'dynamics', 'theory', 'blank'];

async function ids(page: Page, selector: string): Promise<string[]> {
  return page
    .locator(selector)
    .evaluateAll((els) => els.map((e) => e.getAttribute('data-testid') ?? ''));
}

test.describe('Laboratoire — rail, catalogue, bench', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/laboratoire');
    await expect(page.locator('[data-testid="lab-family-rail"]')).toBeVisible();
  });

  test('the rail exposes every family and each swaps the catalogue', async ({ page }) => {
    const rail = await ids(page, '[data-testid="lab-family-rail"] [data-testid^="lab-family-"]');
    expect(rail.sort()).toEqual(FAMILIES.map((f) => `lab-family-${f}`).sort());

    for (const family of FAMILIES) {
      await page.locator(`[data-testid="lab-family-${family}"]`).click();
      await expect(page.locator(`[data-testid="lab-family-${family}"]`)).toHaveAttribute(
        'aria-checked',
        'true'
      );
      await expect(page.locator('[data-testid="lab-catalogue"]')).toBeVisible();
      expect((await ids(page, '[data-testid^="chip-"]')).length).toBeGreaterThan(0);
    }
  });

  test('picking a fiche in the catalogue loads it on the bench', async ({ page }) => {
    const chips = page.locator('[data-testid^="chip-"]');
    const target = chips.nth(1);
    const label = ((await target.textContent()) ?? '').trim();

    await target.click();
    await expect(target).toHaveAttribute('aria-pressed', 'true');
    await expect(page.locator('[data-testid="lab-bench"]')).toContainText(label);
  });

  test('Comparer opens a second bench on another electorate', async ({ page }) => {
    await page.locator('[data-testid="lab-compare"]').click();
    const picker = page.locator('[data-testid="lab-elec-picker"]');
    await expect(picker).toBeVisible();

    await picker.locator('[data-testid^="lab-elec-"]').first().click();
    await expect(page.locator('[data-testid="lab-bench-vs"]')).toBeVisible();
    // Both columns say which electorate they are measured on, and they differ.
    const primary = await page.locator('[data-testid="lab-elec-label-primary"]').textContent();
    const vs = await page.locator('[data-testid="lab-elec-label-vs"]').textContent();
    expect(primary).not.toBe(vs);

    await page.locator('[data-testid="lab-compare-close"]').click();
    await expect(page.locator('[data-testid="lab-bench-vs"]')).toHaveCount(0);
  });
});

// One test per family so a broken fiche names its family and the run stays
// inside the per-test timeout.
test.describe('Laboratoire — every fiche mounts', () => {
  for (const family of FAMILIES) {
    test(`family "${family}": all fiches render on the bench`, async ({ page }) => {
      test.setTimeout(120_000);
      const crashes: string[] = [];
      page.on('pageerror', (err) => crashes.push(err.message));

      await page.goto('/laboratoire');
      await page.locator(`[data-testid="lab-family-${family}"]`).click();

      const chips = await ids(page, '[data-testid^="chip-"]');
      expect(chips.length).toBeGreaterThan(0);

      const broken: string[] = [];
      for (const chip of chips) {
        await page.locator(`[data-testid="${chip}"]`).click();
        const bench = page.locator('[data-testid="lab-bench"]');
        try {
          await expect(bench).toBeVisible({ timeout: 20_000 });
          // The lazy chunk must actually arrive — "Chargement…" is the Suspense
          // fallback, and a fiche stuck on it is a fiche that never loaded.
          await expect(bench).not.toContainText('Chargement…', { timeout: 20_000 });
        } catch {
          broken.push(chip);
        }
      }

      expect(broken, `fiches that never rendered in "${family}"`).toEqual([]);
      expect(crashes, `uncaught errors while sweeping "${family}"`).toEqual([]);
    });
  }
});

// The fiches that call the backend or run a heavy client simulation on demand.
test.describe('Laboratoire — the modules that compute', () => {
  async function openFiche(page: Page, family: string, chip: string) {
    await page.goto('/laboratoire');
    await page.locator(`[data-testid="lab-family-${family}"]`).click();
    await page.locator(`[data-testid="chip-${chip}"]`).click();
    await expect(page.locator('[data-testid="lab-bench"]')).toBeVisible();
  }

  test('the strategic equilibrium module converges to a verdict', async ({ page }) => {
    await openFiche(page, 'rules', 'strat-equilibrium');
    await page.locator('[data-testid="equilibrium-run"]').click();
    await expect(page.locator('[data-testid="equilibrium-headline"]')).toBeVisible({
      timeout: 60_000,
    });
    await expect(page.locator('[data-testid="equilibrium-headline"]')).not.toBeEmpty();
  });

  test('the VSE chart plots one line per compared method', async ({ page }) => {
    await openFiche(page, 'rules', 'anchor-vse');
    await expect(page.locator('[data-testid="vse-chart"]')).toBeVisible({ timeout: 60_000 });
    const lines = page.locator('[data-testid^="vse-line-"]');
    expect(await lines.count()).toBeGreaterThan(1);
  });

  test('the full results table is computed by the backend', async ({ page }) => {
    await openFiche(page, 'theory', 'res-table');
    await page.locator('[data-testid="full-results-run"]').click();

    // A backend error renders an alert instead of the table — fail on it loudly.
    await expect(page.locator('[data-testid="lab-bench"] table').first()).toBeVisible({
      timeout: 60_000,
    });
    await expect(page.locator('[data-testid="lab-bench"]')).not.toContainText('Erreur lors de');
  });

  test('real elections are backtested against every method', async ({ page }) => {
    await openFiche(page, 'theory', 'res-real-election');
    // The fiche is lazily loaded: wait for the panel itself, not just the bench.
    await expect(page.locator('[data-testid="real-election-panel"]')).toBeVisible({
      timeout: 30_000,
    });

    const elections = await ids(
      page,
      '[data-testid="real-election-pick"] [data-testid^="real-election-"]'
    );
    expect(elections.length).toBeGreaterThan(0);

    for (const election of elections) {
      await page.locator(`[data-testid="${election}"]`).click();
      // Every real ballot set must be backtested against every method.
      await expect(
        page.locator('[data-testid="real-election-headline"]'),
        election
      ).not.toBeEmpty();
      await expect(page.locator('[data-testid="real-election-panel"]'), election).not.toContainText(
        'NaN'
      );
    }
  });
});
