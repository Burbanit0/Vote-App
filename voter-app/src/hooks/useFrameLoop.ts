import { useCallback, useEffect, useLayoutEffect, useRef } from 'react';

/**
 * One requestAnimationFrame loop that runs `step` while it returns true. `kick()`
 * starts it (a no-op while it runs), so a scroll or pointer handler can call it on
 * every event and the page does no work once everything has settled.
 */
export function useFrameLoop(step: (now: number) => boolean): () => void {
  const raf = useRef(0);
  const stepRef = useRef(step);
  useLayoutEffect(() => {
    stepRef.current = step;
  });
  const kick = useCallback(() => {
    if (raf.current) return;
    const tick = (now: number) => {
      // Cleared before the step runs: a step that throws must not leave the loop stuck.
      raf.current = 0;
      if (stepRef.current(now)) raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
  }, []);
  useEffect(
    () => () => {
      cancelAnimationFrame(raf.current);
      // StrictMode mounts, unmounts and mounts again: the second mount's kick() must start.
      raf.current = 0;
    },
    []
  );
  return kick;
}
