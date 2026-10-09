import { test, expect } from './coverageFixtures';
import { STORY_CLAIMS, type StoryClaim } from '../../src/lib/storyClaims';
import { storyById } from '../../src/lib/stories';

// The e2e winner oracle (PLAN_BEYOND_CI W1.4). stories.test.ts checks that the engine
// elects the winner each beat's copy names; this plays the stories whose winners are in
// STORY_CLAIMS (today, "five") and checks the winner the reader sees, beat by beat.
type WinnerClaim = Extract<StoryClaim, { kind: 'winner' }>;
const winnerClaims = STORY_CLAIMS.filter((c): c is WinnerClaim => c.kind === 'winner');

for (const id of new Set(winnerClaims.map((c) => c.story))) {
  test(`story "${id}" shows, at each beat, the winner its copy names`, async ({ page }) => {
    const steps = storyById(id)!.steps;
    const claims = winnerClaims.filter((c) => c.story === id);
    // A claim on a step the story no longer has would be skipped silently.
    expect(steps.map((s) => s.id)).toEqual(expect.arrayContaining(claims.map((c) => c.step)));

    await page.goto('/playground');
    await page.locator('[data-testid="story-launch"]').click();
    await page.locator(`[data-testid="story-pick-${id}"]`).click();
    await expect(page.locator('[data-testid="story-bar"]')).toBeVisible();

    const winner = page.locator('[data-testid="field-winner"] strong').first();
    for (const [i, step] of steps.entries()) {
      if (i > 0) await page.locator('[data-testid="story-next"]').click();
      // Wait for this beat's rule, so a winner shared with the last beat is not read early.
      if (step.rule)
        await expect(page.locator('[data-testid="rule-select"]')).toHaveValue(step.rule);
      const claim = claims.find((c) => c.step === step.id);
      if (claim) await expect(winner, `${id}/${step.id}`).toHaveText(claim.expected);
    }
  });
}
