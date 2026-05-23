/**
 * useApi — generic data-fetching hook with loading/error/refetch state.
 *
 * Replaces the boilerplate of:
 *   const [data,    setData]    = useState<T | null>(null);
 *   const [loading, setLoading] = useState(false);
 *   const [error,   setError]   = useState<string | null>(null);
 *   useEffect(() => { setLoading(true); axios.post(...).then(setData)
 *                       .catch(e => setError(e.message)).finally(...) }, [...]);
 *
 * which is duplicated across ~49 Perturber panels.
 *
 * Pass `args=null` to skip the fetch (e.g. when the user hasn't filled the
 * form yet). Pass `manual: true` to disable auto-fetching on mount — useful
 * for "fetch on button click" panels.
 *
 *   const { data, loading, error, refetch } = useApi(
 *     getAbstention,
 *     { num_voters, candidates, seed },
 *     [config],                       // deps that should trigger refetch
 *   );
 *
 * Race-safe: stale responses are dropped if the inputs change mid-flight.
 */
import { useCallback, useEffect, useRef, useState } from 'react';

export interface UseApiResult<T> {
  data:     T | null;
  loading:  boolean;
  error:    string | null;
  /** Re-run the fetcher with the current args. */
  refetch:  () => void;
  /** Manually replace the cached data (e.g. after a local optimistic update). */
  setData:  (next: T | null) => void;
}

interface UseApiOptions {
  /**
   * When true, the hook does NOT auto-fetch on mount or dep change — only
   * runs when `refetch()` is called. Useful for "fetch on submit" panels.
   */
  manual?: boolean;
  /**
   * Custom error formatter. Defaults to `err.message ?? String(err)`.
   * Use when the API surfaces structured errors you want to unwrap.
   */
  toErrorMessage?: (err: unknown) => string;
}

function defaultErrorMessage(err: unknown): string {
  if (err && typeof err === 'object') {
    const anyErr = err as { response?: { data?: { error?: string } }; message?: string };
    return anyErr.response?.data?.error ?? anyErr.message ?? String(err);
  }
  return String(err);
}

export function useApi<T, A>(
  fetcher: (args: A) => Promise<T>,
  args:    A | null,
  deps:    unknown[] = [],
  options: UseApiOptions = {},
): UseApiResult<T> {
  const { manual = false, toErrorMessage = defaultErrorMessage } = options;

  const [data,    setData]    = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState<string | null>(null);

  // Token to drop stale responses if deps change mid-flight or refetch races.
  const requestIdRef = useRef(0);
  // Bumping this triggers the effect (used by refetch()).
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (manual && tick === 0) return;
    if (args === null) return;

    const myId = ++requestIdRef.current;
    setLoading(true);
    setError(null);

    fetcher(args)
      .then((d) => {
        if (requestIdRef.current === myId) setData(d);
      })
      .catch((e) => {
        if (requestIdRef.current === myId) setError(toErrorMessage(e));
      })
      .finally(() => {
        if (requestIdRef.current === myId) setLoading(false);
      });
    // We intentionally omit `fetcher`, `args`, `toErrorMessage` from deps:
    //   - `fetcher` is typically a stable module-level function
    //   - `args` is captured at call time; meaningful changes flow via `deps`
    //   - `toErrorMessage` rarely changes
    // The caller controls re-fetch via the `deps` array (and via refetch()).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  const refetch = useCallback(() => setTick((t) => t + 1), []);

  return { data, loading, error, refetch, setData };
}

// ─────────────────────────────────────────────────────────────────────────────
// useApiAction — for the imperative "fetch on button click" pattern that
// dominates the Perturber panels: state values + a Run button, where the
// fetch carries the *current* state values at click time. The auto-deps
// model of useApi doesn't fit cleanly there.
//
//   const { data, loading, error, run, reset } = useApiAction(getAbstention);
//   <Button onClick={() => run({ demob, influence, numRounds, ...config })}>
//
// Race-safe like useApi (stale responses dropped if a second run() races a
// pending one).
// ─────────────────────────────────────────────────────────────────────────────

export interface UseApiActionResult<T, A> {
  data:    T | null;
  loading: boolean;
  error:   string | null;
  run:     (args: A) => Promise<T | null>;
  reset:   () => void;
  setData: (next: T | null) => void;
}

export function useApiAction<T, A>(
  fetcher: (args: A) => Promise<T>,
  options: UseApiOptions = {},
): UseApiActionResult<T, A> {
  const { toErrorMessage = defaultErrorMessage } = options;

  const [data,    setData]    = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState<string | null>(null);

  const requestIdRef = useRef(0);

  const run = useCallback(async (args: A): Promise<T | null> => {
    const myId = ++requestIdRef.current;
    setLoading(true);
    setError(null);
    try {
      const result = await fetcher(args);
      if (requestIdRef.current === myId) {
        setData(result);
        setLoading(false);
        return result;
      }
      return null;
    } catch (e) {
      if (requestIdRef.current === myId) {
        setError(toErrorMessage(e));
        setLoading(false);
      }
      return null;
    }
    // fetcher / toErrorMessage are intentionally captured at call time
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const reset = useCallback(() => {
    requestIdRef.current++;            // invalidate any in-flight call
    setData(null);
    setError(null);
    setLoading(false);
  }, []);

  return { data, loading, error, run, reset, setData };
}
