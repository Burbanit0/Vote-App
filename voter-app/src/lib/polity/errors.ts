/** An API error as text: FastAPI's body carries `detail`; anything else is shown as it is. */
export function messageOf(error: unknown): string {
  if (error && typeof error === 'object' && 'detail' in error) return String(error.detail);
  return String(error);
}
