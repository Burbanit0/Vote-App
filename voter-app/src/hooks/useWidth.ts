import { useLayoutEffect, useState } from 'react';

/**
 * The width of the element given to the returned ref, `initial` until it is measured.
 *
 * A callback ref, so an element that is swapped for another (a loading state for the
 * loaded view) is observed again. A width of 0 (the element hidden or collapsed) keeps
 * the last real one.
 */
export function useWidth(initial: number): [(element: HTMLElement | null) => void, number] {
  const [element, setElement] = useState<HTMLElement | null>(null);
  const [width, setWidth] = useState(initial);
  useLayoutEffect(() => {
    if (!element) return undefined;
    const observer = new ResizeObserver(([entry]) => {
      if (entry && entry.contentRect.width > 0) setWidth(entry.contentRect.width);
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, [element]);
  return [setElement, width];
}
