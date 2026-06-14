// errorMessage — narrow an `unknown` caught error to a user-facing string.
//
// Lets `catch` blocks use `catch (e: unknown)` (type-safe) instead of `any`:
// it pulls a backend `{ response: { data: { error } } }` message first, then a
// plain `Error.message`, and finally the supplied fallback.

interface ApiErrorShape {
  response?: { data?: { error?: unknown } };
  message?: unknown;
}

export function errorMessage(e: unknown, fallback: string): string {
  if (typeof e === 'object' && e !== null) {
    const o = e as ApiErrorShape;
    const apiError = o.response?.data?.error;
    if (typeof apiError === 'string' && apiError) return apiError;
    if (typeof o.message === 'string' && o.message) return o.message;
  }
  return fallback;
}
