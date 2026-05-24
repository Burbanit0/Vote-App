import '@testing-library/jest-dom';
import { TextEncoder, TextDecoder } from 'util';

Object.assign(global, { TextDecoder, TextEncoder });

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
