import { i18nReady } from './i18n';
import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { initUITheme } from './stores/useUIStore';
import { initAnalytics } from './lib/analytics';

// Apply the persisted theme to <html> at startup (was ThemeProvider's job).
initUITheme();
// Anonymous, cookie-less usage measurement (Umami). No-op unless the
// VITE_UMAMI_* vars were set at build time AND this is a production build.
initAnalytics();

// The query devtools are a devDependency, loaded on demand in development only.
// In a production build this is `null` and the import() is dead code: the
// package is never resolved or bundled. If the chunk fails to load (the dev
// server restarted, deps re-optimized), render nothing rather than letting the
// lazy component's error unmount the whole app.
const ReactQueryDevtools =
  process.env.NODE_ENV !== 'production'
    ? React.lazy(() =>
        import('@tanstack/react-query-devtools').then(
          (m) => ({ default: m.ReactQueryDevtools }),
          () => ({ default: () => null })
        )
      )
    : null;

// Server-state cache. Simulations are deterministic for a given input, so a
// generous staleTime avoids redundant refetches; one retry covers transient
// network blips without masking real errors.
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

const root = ReactDOM.createRoot(document.getElementById('root') as HTMLElement);
// Wait for the active language's translation bundle (fr is bundled and resolves
// instantly; en resolves once its code-split chunk loads) before the first
// paint, so the UI never flashes raw translation keys.
i18nReady.finally(() => {
  root.render(
    <React.StrictMode>
      <QueryClientProvider client={queryClient}>
        <App />
        {/* Dev only, and not under browser automation: the floating toggle overlays the page
            under test, and its logo animates while queries are in flight, which WebKit counted
            into the page's width in the pseudo-locale sweep (/polity, 15 px). */}
        {ReactQueryDevtools && !navigator.webdriver && (
          <React.Suspense fallback={null}>
            <ReactQueryDevtools initialIsOpen={false} />
          </React.Suspense>
        )}
      </QueryClientProvider>
    </React.StrictMode>
  );
});
