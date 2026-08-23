import { test, expect } from '@playwright/test';
import { AxeBuilder } from '@axe-core/playwright';
import { SURFACES, ANCHORS, assertEverySurfaceAnchored } from './routes';

// Surfaces come from src/routes.ts via ./surfaces — one list, no drift.

// Axe rules disabled globally:
//   color-contrast — the maps and charts are SVG with theme-aware colours axe
//     scores against the wrong background; validated by hand in chartColors.ts.
const DISABLED_RULES = ['color-contrast'];

async function audit(page: import('@playwright/test').Page, name: string) {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .disableRules(DISABLED_RULES)
    .analyze();

  // Only critical/serious block; minor/moderate are reported, not gating.
  const blocking = results.violations.filter(
    (v) => v.impact === 'critical' || v.impact === 'serious'
  );
  if (blocking.length > 0) {
    const summary = blocking
      .map(
        (v) =>
          `[${v.impact?.toUpperCase()}] ${v.id}: ${v.description}\n` +
          v.nodes
            .slice(0, 3)
            .map((n) => `    ${n.html.substring(0, 120)}`)
            .join('\n')
      )
      .join('\n\n');
    throw new Error(`${blocking.length} accessibility violation(s) on ${name}:\n\n${summary}`);
  }

  const informational = results.violations.filter(
    (v) => v.impact !== 'critical' && v.impact !== 'serious'
  );
  if (informational.length > 0) {
    console.info(
      `[a11y] ${name}: ${informational.length} minor/moderate — ` +
        informational.map((v) => v.id).join(', ')
    );
  }
}

test.describe('WCAG 2.1 AA — axe-core audit', () => {
  test('every surface in src/routes.ts is audited here', () => {
    assertEverySurfaceAnchored();
  });

  for (const path of SURFACES) {
    test(`${path} has no critical/serious violations`, async ({ page }) => {
      await page.goto(path);
      await expect(page.locator(ANCHORS[path])).toBeVisible();
      await audit(page, path);
    });
  }

  test('the playground passes the audit in dark mode too', async ({ page }) => {
    // Seed the theme the way the store reads it (localStorage 'votelab_theme'),
    // so the page paints dark on first render.
    await page.addInitScript(() => localStorage.setItem('votelab_theme', 'dark'));
    await page.goto('/playground');
    await expect(page.locator('[data-testid="playground-page"]')).toBeVisible();
    await expect(page.locator('html')).toHaveAttribute('data-bs-theme', 'dark');
    await audit(page, 'PlaygroundPage (dark)');
  });

  test('the moment rail is operable with the keyboard', async ({ page }) => {
    await page.goto('/playground');
    const method = page.locator('[data-testid="moment-method"]');
    await method.focus();
    await expect(method).toBeFocused();
    await method.press('Enter');
    await expect(method).toHaveAttribute('aria-checked', 'true');
    await expect(page.locator('[data-testid="moment-method-panel"]')).toBeVisible();
  });
});
