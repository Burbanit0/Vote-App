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
import { useAuthStore } from '../stores/useAuthStore';

const API_BASE = process.env.VITE_API_URL || 'http://localhost:4434';

/**
 * Current Bearer token, or null. Source of truth = useAuthStore; falls back to
 * localStorage['user'] (covers the brief window before the store hydrates, and
 * any non-React caller).
 */
export function getAccessToken(): string | null {
  const fromStore = useAuthStore.getState().user?.access_token;
  if (fromStore) return fromStore;
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

/**
 * Legacy service-layer helper — POST that resolves to the parsed body and
 * throws on transport/HTTP error (the axios-on-error-throws contract the
 * `services/*Api.ts` wrappers rely on). Routes through the
 * typed `apiClient` (auth middleware + baseUrl) but takes a plain string path
 * so the pre-response_model service wrappers don't need per-path generics.
 * Panels use the fully-typed `$api`/`apiClient` directly instead.
 */
export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const { data, error } = await (apiClient.POST as any)(path, { body });
  if (error) throw error instanceof Error ? error : new Error('Request failed');
  return data as T;
}

/** GET counterpart of {@link apiPost}; `query` becomes the URL query string. */
export async function apiGet<T>(path: string, query?: Record<string, unknown>): Promise<T> {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const { data, error } = await (apiClient.GET as any)(path, query ? { params: { query } } : {});
  if (error) throw error instanceof Error ? error : new Error('Request failed');
  return data as T;
}

/** DELETE counterpart of {@link apiPost}; resolves to the parsed body (often void). */
export async function apiDelete<T = void>(path: string): Promise<T> {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const { data, error } = await (apiClient.DELETE as any)(path, {});
  if (error) throw error instanceof Error ? error : new Error('Request failed');
  return data as T;
}
