/**
 * apiVersion — runtime selector between the legacy Flask `/api/*` routes
 * and the new FastAPI `/api/v2/*` routes (Phase 2-3 of the strategic
 * refactor — see STRATEGIC_REFACTOR_PLAN.md).
 *
 * Strategy: every endpoint that has been migrated to FastAPI is listed in
 * `MIGRATED_ENDPOINTS` below. `apiPath('election/simulate')` returns
 *   '/api/v2/election/simulate'  if the endpoint is migrated AND the user
 *                                hasn't overridden via the rollback switch
 *   '/api/election/simulate'      otherwise
 *
 * Rollback switches (in order of precedence) — useful if v2 misbehaves
 * in production and you need to flip back to Flask quickly:
 *
 *   1. URL query string:    ?apiV1=1       (per-tab override, ephemeral)
 *   2. localStorage:        votelab_force_api_v1 = "true"
 *                                          (per-browser, persistent)
 *   3. env var:             VITE_FORCE_API_V1=1 at build time
 *
 * When all 35 election endpoints are migrated (end of Phase 3) and the
 * Flask routes are deleted (Phase 4), this file becomes a no-op stub and
 * can be removed.
 */

/** Endpoints currently served by FastAPI on /api/v2/*. Order doesn't matter. */
export const MIGRATED_ENDPOINTS: ReadonlySet<string> = new Set([
  // Phase 2 + Phase 3 batches 1-2 (typed responses)
  'election/simulate',
  'election/combined-effects',
  'election/campaign-sensitivity',
  'election/coalition',
  'election/abstention',
  // Phase 3 batch 3 (passthrough responses)
  'election/nota',
  'election/ballot-complexity',
  'election/shy-voter',
  'election/electoral-fatigue',
]);

/** localStorage key for the rollback switch. Public so tests can clear it. */
export const FORCE_V1_LS_KEY = 'votelab_force_api_v1';

/** Query string parameter that forces v1 for this browser tab. */
export const FORCE_V1_QUERY_PARAM = 'apiV1';

/** Build-time env var read from Vite. */
const ENV_FORCE_V1: boolean = (
  // process.env at build time (also defined in jest.config so tests work)
  // eslint-disable-next-line no-undef
  typeof process !== 'undefined' && process.env?.VITE_FORCE_API_V1 === '1'
);

/** Returns true if the caller should fall back to Flask /api/* for everything. */
export function shouldForceV1(): boolean {
  if (ENV_FORCE_V1) return true;

  if (typeof window !== 'undefined') {
    try {
      const params = new URLSearchParams(window.location.search);
      if (params.get(FORCE_V1_QUERY_PARAM) === '1') return true;
    } catch {
      // Some test envs don't expose window.location.search
    }
    try {
      if (window.localStorage.getItem(FORCE_V1_LS_KEY) === 'true') return true;
    } catch {
      // localStorage unavailable (SSR, private browsing) — ignore
    }
  }
  return false;
}

/**
 * Resolve an endpoint slug to the correct URL path.
 *
 *   apiPath('election/simulate')          -> '/api/v2/election/simulate'
 *   apiPath('election/abstention')        -> '/api/election/abstention'   (not migrated yet)
 *   apiPath('election/simulate', { v1: true })  -> '/api/election/simulate'
 *
 * The slug should NOT include a leading slash and should NOT include the
 * `api/` prefix — both are added by this helper.
 */
export function apiPath(slug: string, opts: { v1?: boolean } = {}): string {
  const normalized = slug.replace(/^\/+/, '').replace(/^api\/(v2\/)?/, '');
  const forceV1 = opts.v1 || shouldForceV1();
  if (!forceV1 && MIGRATED_ENDPOINTS.has(normalized)) {
    return `/api/v2/${normalized}`;
  }
  return `/api/${normalized}`;
}
