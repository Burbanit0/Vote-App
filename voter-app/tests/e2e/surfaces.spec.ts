import { test, expect } from '@playwright/test';

// The two surfaces that flank the playground: the Laboratoire (a rail of
// families → a catalogue of fiches → one full-width bench) and À vous de jouer
// (cast one ballot yourself, then read what it was worth).

test.describe('Laboratoire — rail, catalogue, bench', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/laboratoire');
    await expect(page.locator('[data-testid="lab-family-rail"]')).toBeVisible();
  });

  test('picking a family swaps the catalogue and keeps a bench mounted', async ({ page }) => {
    await expect(page.locator('[data-testid="lab-bench"]')).toBeVisible();

    for (const family of ['rules', 'systems', 'blank']) {
      await page.locator(`[data-testid="lab-family-${family}"]`).click();
      await expect(page.locator(`[data-testid="lab-family-${family}"]`)).toHaveAttribute(
        'aria-checked',
        'true'
      );
      await expect(page.locator('[data-testid="lab-catalogue"]')).toBeVisible();
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

    await page.locator('[data-testid="lab-compare-close"]').click();
    await expect(page.locator('[data-testid="lab-bench-vs"]')).toHaveCount(0);
  });
});

test.describe('À vous de jouer — one ballot, sealed', () => {
  test('casting a ballot seals it and produces a verdict', async ({ page }) => {
    await page.goto('/a-vous-de-jouer');

    await page.locator('[data-testid="play-vote-open"]').click();
    await expect(page.locator('[data-testid="play-booth"]')).toBeVisible();

    await page.locator('[data-testid="play-cast"]').click();

    // The ballot is sealed — it cannot be edited in place any more…
    await expect(page.locator('[data-testid="play-sealed-strip"]')).toBeVisible();
    await expect(page.locator('[data-testid="play-vote-open"]')).toHaveCount(0);
    // …and the analysis of that vote is what you get instead.
    await expect(page.locator('[data-testid="play-verdict"]')).not.toBeEmpty();
    await expect(page.locator('[data-testid="play-winner"]')).not.toBeEmpty();
  });

  test('moving the bloc slider re-reads the same sealed ballot', async ({ page }) => {
    await page.goto('/a-vous-de-jouer');
    await page.locator('[data-testid="play-vote-open"]').click();
    await page.locator('[data-testid="play-cast"]').click();

    const verdict = page.locator('[data-testid="play-verdict"]');
    await expect(verdict).toBeVisible();

    // "How many people like you would it take" — the slider re-runs the election.
    // Its max depends on the electorate size, so drive it to whatever that is.
    const bloc = page.locator('[data-testid="play-bloc"]');
    const max = (await bloc.getAttribute('max')) ?? '2';
    await bloc.fill(max);
    await expect(bloc).toHaveValue(max);
    await expect(verdict).not.toBeEmpty();
  });
});
