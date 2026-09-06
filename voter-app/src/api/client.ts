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

// Same origin in production ('' → relative /api). The prod build bakes '' via
// vite define; `??` preserves that empty string (unlike `||`, which would fall
// back to localhost), while an unset var (test env) falls back to localhost.
const API_BASE = process.env.VITE_API_URL ?? 'http://localhost:4434';

export const apiClient = createClient<paths>({ baseUrl: API_BASE });

/**
 * Thrown by apiPost/apiGet/apiDelete on a non-2xx response. Carries the HTTP
 * status and the parsed error body (FastAPI's HTTPException shape is
 * `{ detail: string | object }`, but any endpoint's error payload survives on
 * `.body` even if it doesn't match that shape) so callers can distinguish
 * "offline/unreachable" from "the server rejected this request" instead of
 * catching an opaque `Error('Request failed')`.
 */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly body: unknown
  ) {
    super(ApiError.messageFor(status, body));
    this.name = 'ApiError';
  }

  private static messageFor(status: number, body: unknown): string {
    if (body && typeof body === 'object' && 'detail' in body) {
      const { detail } = body as { detail: unknown };
      if (typeof detail === 'string') return detail;
    }
    return `Request failed with status ${status}`;
  }
}

/**
 * Legacy service-layer helper — POST that resolves to the parsed body and
 * throws on transport/HTTP error (the axios-on-error-throws contract the
 * `services/*Api.ts` wrappers rely on). Routes through the
 * typed `apiClient` (auth middleware + baseUrl) but takes a plain string path
 * so the pre-response_model service wrappers don't need per-path generics.
 * Panels use the fully-typed `$api`/`apiClient` directly instead.
 */
export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const { data, error, response } = await (apiClient.POST as any)(path, { body });
  if (error !== undefined) throw new ApiError(response.status, error);
  return data as T;
}

/** GET counterpart of {@link apiPost}; `query` becomes the URL query string. */
export async function apiGet<T>(path: string, query?: Record<string, unknown>): Promise<T> {
  const { data, error, response } = await (apiClient.GET as any)(
    path,
    query ? { params: { query } } : {}
  );
  if (error !== undefined) throw new ApiError(response.status, error);
  return data as T;
}

/** DELETE counterpart of {@link apiPost}; resolves to the parsed body (often void). */
export async function apiDelete<T = void>(path: string): Promise<T> {
  const { data, error, response } = await (apiClient.DELETE as any)(path, {});
  if (error !== undefined) throw new ApiError(response.status, error);
  return data as T;
}
