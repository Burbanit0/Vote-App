/**
 * api/client.ts — the typed HTTP client (Phase 5).
 *
 * openapi-fetch instance typed against the generated `paths` (src/api/types.gen.ts,
 * itself generated from the FastAPI OpenAPI schema). Request bodies, query params
 * and — where a route declares a response_model — response shapes are all checked
 * at compile time.
 *
 * The app is fully anonymous — no auth headers, no token. Every endpoint the
 * frontend still calls is public.
 */
import createClient from 'openapi-fetch';
import type { paths } from './types.gen';

// Empty string in production = same origin (the container serving this build).
// Vite's define bakes the value (localhost in dev, '' in prod); `?? ''` only
// guards the type — it must not clobber the intentional empty string.
const API_BASE = process.env.VITE_API_URL ?? '';

export const apiClient = createClient<paths>({ baseUrl: API_BASE });

/**
 * Legacy service-layer helper — POST that resolves to the parsed body and
 * throws on transport/HTTP error (the axios-on-error-throws contract the
 * `services/*Api.ts` wrappers rely on). Routes through the
 * typed `apiClient` (auth middleware + baseUrl) but takes a plain string path
 * so the pre-response_model service wrappers don't need per-path generics.
 * Panels use the fully-typed `$api`/`apiClient` directly instead.
 */
export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const { data, error } = await (apiClient.POST as any)(path, { body });
  if (error) throw error instanceof Error ? error : new Error('Request failed');
  return data as T;
}

/** GET counterpart of {@link apiPost}; `query` becomes the URL query string. */
export async function apiGet<T>(path: string, query?: Record<string, unknown>): Promise<T> {
  const { data, error } = await (apiClient.GET as any)(path, query ? { params: { query } } : {});
  if (error) throw error instanceof Error ? error : new Error('Request failed');
  return data as T;
}

/** DELETE counterpart of {@link apiPost}; resolves to the parsed body (often void). */
export async function apiDelete<T = void>(path: string): Promise<T> {
  const { data, error } = await (apiClient.DELETE as any)(path, {});
  if (error) throw error instanceof Error ? error : new Error('Request failed');
  return data as T;
}
