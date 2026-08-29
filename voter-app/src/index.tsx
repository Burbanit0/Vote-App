import { i18nReady } from './i18n';
import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { initUITheme } from './stores/useUIStore';
import { initAnalytics } from './lib/analytics';

// Apply the persisted theme to <html> at startup (was ThemeProvider's job).
initUITheme();
// Anonymous, cookie-less usage measurement (Umami). No-op unless the
// VITE_UMAMI_* vars were set at build time AND this is a production build.
initAnalytics();

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
        {process.env.NODE_ENV !== 'production' && <ReactQueryDevtools initialIsOpen={false} />}
      </QueryClientProvider>
    </React.StrictMode>
  );
});
