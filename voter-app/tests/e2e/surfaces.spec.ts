import { test, expect } from '@playwright/test';

// The two entry surfaces around the instrument: Découvrir (the guided demo of
// the thesis) and À vous de jouer (cast one ballot yourself, then read what it
// was worth). Both run entirely client-side on the same voting engine.

test.describe('Découvrir — the thesis, one step at a time', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/decouvrir');
    await expect(page.locator('[data-testid="discover-winner"]')).toBeVisible();
  });

  test('the four demo rules do not all elect the same candidate', async ({ page }) => {
    const winner = page.locator('[data-testid="discover-winner"]');
    const tabs = page.getByRole('tab');
    const count = await tabs.count();
    expect(count).toBe(4);

    const seen = new Set<string>();
    for (let i = 0; i < count; i++) {
      await tabs.nth(i).click();
      await expect(tabs.nth(i)).toHaveAttribute('aria-selected', 'true');
      await expect(winner).not.toBeEmpty();
      seen.add(((await winner.textContent()) ?? '').trim());
    }
    // Same ballots, four counting rules: the page exists because they disagree.
    expect(seen.size).toBeGreaterThan(1);
  });
});

test.describe('À vous de jouer — one ballot, sealed', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/a-vous-de-jouer');
    await expect(page.locator('[data-testid="play-vote-open"]')).toBeVisible();
  });

  test('casting a ballot seals it and produces a verdict', async ({ page }) => {
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

  test('every ballot language can be cast and is counted', async ({ page }) => {
    const crashes: string[] = [];
    page.on('pageerror', (err) => crashes.push(err.message));

    for (const lang of ['one', 'rank', 'approve', 'score', 'points']) {
      await page.goto('/a-vous-de-jouer');
      await page.locator('[data-testid="play-vote-open"]').click();
      await page.locator(`[data-testid="play-lang-${lang}"]`).click();
      await expect(page.locator(`[data-testid="play-lang-${lang}"]`)).toHaveAttribute(
        'aria-checked',
        'true'
      );
      await page.locator('[data-testid="play-cast"]').click();

      await expect(page.locator('[data-testid="play-verdict"]'), lang).not.toBeEmpty();
      // A ballot language only unlocks the methods it can actually feed.
      const methods = page.locator('[data-testid="play-methods"] [data-testid^="play-rule-"]');
      expect(await methods.count(), `no method for ballot language ${lang}`).toBeGreaterThan(0);
    }
    expect(crashes).toEqual([]);
  });

  test('each posture is analysed on its own terms', async ({ page }) => {
    for (const posture of ['sincere', 'strategic', 'abstain']) {
      await page.goto('/a-vous-de-jouer');
      await page.locator('[data-testid="play-vote-open"]').click();
      await page.locator(`[data-testid="play-posture-${posture}"]`).click();
      await page.locator('[data-testid="play-cast"]').click();

      await expect(page.locator('[data-testid="play-verdict"]'), posture).not.toBeEmpty();
      await expect(page.locator('[data-testid="play-verdict"]'), posture).not.toContainText('NaN');
    }
  });

  test('moving the bloc slider re-reads the same sealed ballot', async ({ page }) => {
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
