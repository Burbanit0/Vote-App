/**
 * apiVersion — resolves an endpoint slug to its backend URL.
 *
 * The backend is FastAPI-only (Flask was retired in Phase 4.5.b of the strategic
 * refactor), so every Election Lab / theory / simulations / scenarios / auth
 * endpoint lives under `/api/v2/*`. This helper just normalises a slug and
 * prefixes it. (The public research API at `/api/v1/*` is addressed directly,
 * not through this helper.)
 *
 * The old Flask `/api/*` rollback switches (?apiV1=1, localStorage,
 * VITE_FORCE_API_V1) were removed with Flask — there is nothing to roll back to.
 */

/**
 * Resolve an endpoint slug to its `/api/v2/*` path.
 *
 *   apiPath('election/simulate')           -> '/api/v2/election/simulate'
 *   apiPath('/api/v2/election/simulate')   -> '/api/v2/election/simulate'
 *   apiPath('scenarios')                   -> '/api/v2/scenarios'
 *
 * The slug may omit or include a leading slash and/or an `api/`/`api/v2/`
 * prefix — all are normalised away before re-prefixing.
 */
export function apiPath(slug: string): string {
  const normalized = slug.replace(/^\/+/, '').replace(/^api\/(v2\/)?/, '');
  return `/api/v2/${normalized}`;
}
