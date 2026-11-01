import { useEffect, useRef } from 'react';

/**
 * For a section marked `data-reveal`: sets `data-shown` on it the first time it comes
 * into view, which lets the entrance animations the CSS holds paused until then run
 * (tailwind.css). No React state: nothing re-renders.
 */
export function useReveal<T extends Element>() {
  const ref = useRef<T>(null);
  useEffect(() => {
    const el = ref.current!;
    const io = new IntersectionObserver(
      ([e]) => {
        if (!e.isIntersecting) return;
        io.disconnect();
        el.setAttribute('data-shown', '');
      },
      { threshold: 0.15 }
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return ref;
}
