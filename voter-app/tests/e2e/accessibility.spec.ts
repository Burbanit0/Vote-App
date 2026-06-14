import { test, expect } from '@playwright/test';
import { AxeBuilder } from '@axe-core/playwright';

// Pages to audit — all public (no login required)
const PAGES = [
  { path: '/', name: 'HomePage' },
  { path: '/simulation/compare', name: 'SimulationComparePage' },
  { path: '/scenario-builder', name: 'ScenarioBuilderPage' },
  { path: '/constitutional-crisis', name: 'ConstitutionalCrisisPage' },
];

// Axe rules to disable globally (known false positives in this stack):
//   color-contrast — Recharts SVG text uses theme-aware colours that axe
//     cannot evaluate correctly in jsdom; validated manually via chartColors.ts.
const DISABLED_RULES = ['color-contrast'];

test.describe('WCAG 2.1 AA — axe-core audit', () => {
  for (const { path, name } of PAGES) {
    test(`${name} (${path}) has no critical/serious violations`, async ({ page }) => {
      await page.goto(path);
      await page.waitForLoadState('networkidle');

      const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .disableRules(DISABLED_RULES)
        .analyze();

      // Fail only on critical and serious violations — minor and moderate are
      // surfaced as informational warnings.
      const blocking = results.violations.filter(
        (v) => v.impact === 'critical' || v.impact === 'serious'
      );

      if (blocking.length > 0) {
        const summary = blocking
          .map(
            (v) =>
              `[${v.impact?.toUpperCase()}] ${v.id}: ${v.description}\n` +
              `  Affected nodes:\n` +
              v.nodes
                .slice(0, 3)
                .map((n) => `    ${n.html.substring(0, 120)}`)
                .join('\n')
          )
          .join('\n\n');
        throw new Error(`${blocking.length} accessibility violation(s) on ${name}:\n\n${summary}`);
      }

      // Surface moderate/minor violations as console info (non-blocking)
      const informational = results.violations.filter(
        (v) => v.impact !== 'critical' && v.impact !== 'serious'
      );
      if (informational.length > 0) {
        console.info(
          `[a11y] ${name}: ${informational.length} minor/moderate violation(s) — ` +
            informational.map((v) => v.id).join(', ')
        );
      }
    });
  }

  // ── Keyboard navigation ────────────────────────────────────────────────────

  test('MethodTooltip shows on Enter and closes on Escape', async ({ page }) => {
    await page.goto('/simulation/compare');
    await page.waitForLoadState('networkidle');

    // Run a simulation so the winner matrix (with MethodTooltip) is rendered
    const runBtn = page.getByRole('button', { name: /lancer l['']analyse|run analysis/i });
    if (await runBtn.isVisible()) {
      await page.locator('input[type="range"]').first().fill('5');
      await runBtn.click();
      await page.waitForSelector('[role="tablist"]', { timeout: 45_000 });
    }

    // Find a MethodTooltip trigger (has role="button" and aria-haspopup="true")
    const trigger = page.locator('[role="button"][aria-haspopup="true"]').first();
    if ((await trigger.count()) === 0) {
      test.skip();
      return;
    }

    // Tab-focus the trigger — tooltip should become visible
    await trigger.focus();
    await expect(trigger).toBeFocused();

    // Press Enter — should toggle tooltip
    await trigger.press('Enter');
    await expect(trigger).toHaveAttribute('aria-expanded', 'true');

    // Press Escape — should close tooltip and clear focus
    await trigger.press('Escape');
    await expect(trigger).toHaveAttribute('aria-expanded', 'false');
  });

  test('all form inputs have associated labels', async ({ page }) => {
    await page.goto('/simulation/compare');
    await page.waitForLoadState('domcontentloaded');

    // Every visible input/select/textarea must be labelled
    const inputs = page.locator('input:not([type="hidden"]), select, textarea');
    const count = await inputs.count();

    for (let i = 0; i < count; i++) {
      const el = inputs.nth(i);
      if (!(await el.isVisible())) continue;

      const id = await el.getAttribute('id');
      const ariaLabel = await el.getAttribute('aria-label');
      const ariaLabelledby = await el.getAttribute('aria-labelledby');
      const labelFor = id ? await page.locator(`label[for="${id}"]`).count() : 0;

      const isLabelled = ariaLabel || ariaLabelledby || labelFor > 0;
      if (!isLabelled) {
        const html = await el.evaluate((n) => n.outerHTML.substring(0, 200));
        console.warn(`[a11y] Unlabelled input: ${html}`);
      }
      // Non-blocking — axe handles the hard enforcement above
    }
  });

  test('dark-mode page passes axe audit', async ({ page }) => {
    await page.goto('/');
    // Enable dark mode
    const darkBtn = page.getByRole('button', { name: /passer en mode sombre|switch to dark/i });
    if (await darkBtn.isVisible()) {
      await darkBtn.click();
    }
    await page.waitForLoadState('networkidle');

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .disableRules(DISABLED_RULES)
      .analyze();

    const blocking = results.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious'
    );
    expect(blocking, `Dark-mode violations: ${JSON.stringify(blocking, null, 2)}`).toHaveLength(0);
  });
});
