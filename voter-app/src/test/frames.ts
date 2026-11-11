import { vi } from 'vitest';

/**
 * Takes over requestAnimationFrame so a test steps frames by hand. The clock starts
 * at performance.now() and moves `dt` ms a frame; wrap `flush` in act() when the
 * frames set React state.
 */
export function manualFrames() {
  let queue: FrameRequestCallback[] = [];
  let now = performance.now();
  vi.spyOn(window, 'requestAnimationFrame').mockImplementation((cb) => queue.push(cb));
  vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => {});
  /** Runs frames until none is queued, or `max` of them; returns how many ran. */
  const flush = (max = 1000, dt = 16) => {
    let n = 0;
    while (queue.length && n < max) {
      const run = queue;
      queue = [];
      now += dt;
      run.forEach((cb) => cb(now));
      n++;
    }
    return n;
  };
  return { flush, pending: () => queue.length };
}

/**
 * Sets window.scrollY (jsdom never scrolls), makes scrollTo move it, and lays every
 * element out at the top of the document, so its viewport rect moves up as the page
 * scrolls down.
 */
export function fakeScroll(initial = 0) {
  let y = initial;
  Object.defineProperty(window, 'scrollY', { configurable: true, get: () => y });
  vi.spyOn(Element.prototype, 'getBoundingClientRect').mockImplementation(
    () => ({ top: -y, left: 0, right: 0, bottom: -y, width: 0, height: 0, x: 0, y: -y }) as DOMRect
  );
  const scrollTo = vi.fn((a: number | ScrollToOptions, b?: number) => {
    y = typeof a === 'number' ? (b as number) : (a.top as number);
  });
  window.scrollTo = scrollTo as unknown as typeof window.scrollTo;
  return {
    scrollTo,
    set: (v: number) => {
      y = v;
      window.dispatchEvent(new Event('scroll'));
    },
    get: () => y,
  };
}

/** A matchMedia whose answers a test chooses, by substring of the query. */
export function fakeMedia(matches: Record<string, boolean>) {
  window.matchMedia = vi.fn((query: string) => ({
    matches: Object.entries(matches).some(([k, v]) => v && query.includes(k)),
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
  })) as unknown as typeof window.matchMedia;
}
