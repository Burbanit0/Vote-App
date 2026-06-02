import { i18nReady } from './i18n';
import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import reportWebVitals from './reportWebVitals';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { initUITheme } from './stores/useUIStore';

const googleClientId = process.env.VITE_GOOGLE_CLIENT_ID || '';

// Apply the persisted theme to <html> at startup (was ThemeProvider's job).
initUITheme();

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
        <GoogleOAuthProvider clientId={googleClientId}>
          <App />
        </GoogleOAuthProvider>
        {process.env.NODE_ENV !== 'production' && (
          <ReactQueryDevtools initialIsOpen={false} />
        )}
      </QueryClientProvider>
    </React.StrictMode>
  );
});

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
