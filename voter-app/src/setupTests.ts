import '@testing-library/jest-dom';
import { vi } from 'vitest';
import { TextEncoder, TextDecoder } from 'util';

Object.assign(global, { TextDecoder, TextEncoder });

// @testing-library/react auto-advances fake timers inside `waitFor()` by calling
// a GLOBAL `jest.advanceTimersByTime(...)`. Vitest exposes `vi`, not `jest`, so
// without this shim every `waitFor` under `vi.useFakeTimers()` hangs to the test
// timeout. Provide a minimal `jest` global mapping the methods testing-library
// uses to their `vi` equivalents. (Runtime `jest.*` test calls were migrated to
// `vi.*`; this object is only consumed by testing-library internals.)
(globalThis as unknown as { jest: unknown }).jest = {
  advanceTimersByTime: (ms: number) => vi.advanceTimersByTime(ms),
  advanceTimersToNextTimer: () => vi.advanceTimersToNextTimer(),
};

// jsdom doesn't implement window.matchMedia — required by every component
// that does responsive checks (ElectionLabPage, several Simulation/* charts).
// Polyfill returns a minimal MediaQueryList that always reports "not matching".
if (typeof window !== 'undefined' && !window.matchMedia) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: (query: string) => ({
      matches:             false,
      media:               query,
      onchange:            null,
      addListener:         () => {},      // legacy API still used by some libs
      removeListener:      () => {},
      addEventListener:    () => {},
      removeEventListener: () => {},
      dispatchEvent:       () => false,
    }),
  });
}

// jsdom also lacks ResizeObserver — used by recharts <ResponsiveContainer>
// and any component that watches its own size.
if (typeof window !== 'undefined' && !(window as any).ResizeObserver) {
  (window as any).ResizeObserver = class {
    observe()    {}
    unobserve()  {}
    disconnect() {}
  };
}

// Initialize i18next so components using useTranslation() work in Jest.
// This mirrors the import in src/index.tsx.
import './i18n';
