/**
 * The app's route table, as data.
 *
 * Single source of truth: App.tsx builds its <Route> elements from here, and the
 * Playwright suite imports the same lists (tests/e2e/surfaces.ts). Adding or
 * retiring a route therefore changes what e2e covers in the same commit —
 * the suite cannot silently keep testing a page that no longer exists, which is
 * exactly how it rotted for two months.
 */

/** The five real surfaces — everything else is a redirect or the 404. */
export const SURFACES = [
  '/',
  '/decouvrir',
  '/a-vous-de-jouer',
  '/playground',
  '/laboratoire',
] as const;

export type Surface = (typeof SURFACES)[number];

/**
 * Retired routes → where they land now. Content was folded into the playground
 * (do) or the laboratoire (go deeper); auth is gone entirely (the app is
 * anonymous). Old and bookmarked links redirect instead of 404-ing.
 */
export const LEGACY_REDIRECTS: Record<string, Surface> = {
  '/what-if': '/playground',
  '/campagne': '/playground',
  '/election-lab': '/playground',
  '/sortition': '/playground',
  '/party-dynamics': '/playground',
  '/scenario-builder': '/playground',
  '/simulation/compare': '/playground',
  '/simulation': '/playground',
  '/theory': '/laboratoire',
  '/quiz': '/laboratoire',
  '/regimes-internationaux': '/laboratoire',
  '/quadratic-funding': '/laboratoire',
  '/tech-democracy': '/laboratoire',
  '/api-docs': '/laboratoire',
  '/galerie': '/laboratoire',
  // Auth removed — accounts and community are gone.
  '/login': '/',
  '/register': '/',
  '/oauth/callback': '/',
  '/profile': '/',
  '/users/:id': '/',
};
