/**
 * api/client.ts — the typed HTTP client (Phase 5).
 *
 * openapi-fetch instance typed against the generated `paths` (src/api/types.gen.ts,
 * itself generated from the FastAPI OpenAPI schema). Request bodies, query params
 * and — where a route declares a response_model — response shapes are all checked
 * at compile time.
 *
 * An auth middleware attaches the Bearer token on every request, so panels never
 * deal with auth headers (the old per-service getAuthHeader() helpers go away).
 * The token currently lives in localStorage['user'].access_token; once the auth
 * Zustand store lands (Phase 5.4) this reads from there instead.
 */
import createClient, { type Middleware } from 'openapi-fetch';
import type { paths } from './types.gen';

const API_BASE = process.env.VITE_API_URL || 'http://localhost:4434';

/** Current Bearer token, or null. Source of truth = localStorage['user']. */
export function getAccessToken(): string | null {
  try {
    const raw = localStorage.getItem('user');
    if (!raw) return null;
    const token = (JSON.parse(raw) as { access_token?: string }).access_token;
    return token ?? null;
  } catch {
    return null;
  }
}

const authMiddleware: Middleware = {
  async onRequest({ request }) {
    const token = getAccessToken();
    if (token) request.headers.set('Authorization', `Bearer ${token}`);
    return request;
  },
};

export const apiClient = createClient<paths>({ baseUrl: API_BASE });
apiClient.use(authMiddleware);
