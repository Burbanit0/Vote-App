import { SURFACES, LEGACY_REDIRECTS, type Surface } from '../../src/routes';
import { expect, type Page } from './coverageFixtures';

export { SURFACES, LEGACY_REDIRECTS, type Surface };

/**
 * What proves a surface actually rendered — a data-testid owned by the page, not
 * a CSS class or a translated string (both move; testids are the contract).
 *
 * Typed as a complete Record over SURFACES: adding a route to src/routes.ts and
 * forgetting it here is caught at runtime by `assertEverySurfaceAnchored`, which
 * every navigation/a11y/i18n run calls.
 */
export const ANCHORS: Record<Surface, string> = {
  '/': '[data-testid="home-hero"]',
  '/decouvrir': '[data-testid="discover-winner"]',
  '/a-vous-de-jouer': '[data-testid="play-vote-open"]',
  '/playground': '[data-testid="playground-page"]',
  '/laboratoire': '[data-testid="lab-family-rail"]',
  '/polity': '[data-testid="polity-page"]',
};

/** Route patterns carry params ("/users/:id"); browsers need a concrete URL. */
/**
 * Wait until `path` has rendered its anchor (its lazy chunk loaded) before navigating
 * again, or before the test ends. A navigation that cancels a page's in-flight requests
 * can crash WebKit's network process ("WebKit encountered an internal error",
 * microsoft/playwright#42803). f7c5f6f8 removed that shape once, spec by spec, and it came back.
 */
export const settled = (page: Page, path: Surface): Promise<void> =>
  expect(page.locator(ANCHORS[path])).toBeVisible();

export const concreteUrl = (pattern: string): string => pattern.replace(/:\w+/g, '1');

/** The guard against silent under-coverage: a new surface with no anchor fails. */
export function assertEverySurfaceAnchored(): void {
  const missing = SURFACES.filter((path) => !ANCHORS[path]);
  if (missing.length > 0) {
    throw new Error(
      `Route(s) added to src/routes.ts with no e2e anchor: ${missing.join(', ')}. ` +
        `Add a data-testid the page owns to ANCHORS in tests/e2e/surfaces.ts.`
    );
  }
}
