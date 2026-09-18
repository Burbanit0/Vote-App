import { useEffect, useRef } from 'react';

/** Slider-drag debounce shared by the Laboratoire panels. */
export const DEBOUNCE_MS = 400;

/**
 * `fn`, called once the caller stops calling for `delay` ms.
 *
 * Fourteen panels hand-rolled this; ten of them forgot the unmount cleanup, so
 * leaving a fiche mid-debounce still fired the request at an unmounted panel.
 * Cleanup lives here so it cannot be the part someone leaves out.
 *
 * Not memoized on purpose: nothing reads the returned identity, and a
 * `useCallback` over a per-render `fn` would memoize nothing anyway.
 */
export function useDebouncedCallback<A extends unknown[]>(
  fn: (...args: A) => void,
  delay: number = DEBOUNCE_MS
): (...args: A) => void {
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Newest closure, not the one captured when the timer was armed: `fn` reads
  // state the pending call has to see.
  const latest = useRef(fn);
  latest.current = fn;

  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
    },
    []
  );

  return (...args: A) => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => latest.current(...args), delay);
  };
}
