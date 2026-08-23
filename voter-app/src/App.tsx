import React, { Suspense } from 'react';
import { BrowserRouter as Router, Route, Routes, Navigate } from 'react-router';
import { Spinner } from '@/components/ui/spinner';

import Navbar from './components/Navbar';
import ErrorBoundary from './components/Route/ErrorBoundary';
import { LEGACY_REDIRECTS } from './routes';

// ── Eager imports — small, on the critical first-paint path ─────────────────
import HomePage from './pages/HomePage';

// ── Lazy imports — heavier pages, code-split into separate chunks so the
//    HomePage download doesn't drag in everything. Each becomes its own chunk.
const PlaygroundPage = React.lazy(() => import('./pages/PlaygroundPage'));
const LaboratoirePage = React.lazy(() => import('./pages/LaboratoirePage'));
const DecouvrirPage = React.lazy(() => import('./pages/DecouvrirPage'));
const AVousDeJouerPage = React.lazy(() => import('./pages/AVousDeJouerPage'));
const NotFoundPage = React.lazy(() => import('./pages/NotFoundPage'));

import { useTheme } from './stores/useUIStore';
import { ToastProvider } from './components/shared/ToastNotification';
import { ElectionProvider } from './stores/useElectionStore';
import UpdatePrompt from './components/shared/UpdatePrompt';
import OfflineBanner from './components/shared/OfflineBanner';

import './styles/tailwind.css';

const RouteFallback: React.FC = () => (
  <div className="flex justify-center items-center py-5" data-testid="route-fallback">
    <Spinner role="status" size="sm" className="me-2" />
    <span className="text-muted-foreground text-sm">Chargement…</span>
  </div>
);

const AppContent: React.FC = () => {
  const { theme } = useTheme();

  return (
    <div className="App" data-bs-theme={theme}>
      <OfflineBanner />
      <Navbar />
      <ErrorBoundary>
        <Suspense fallback={<RouteFallback />}>
          <Routes>
            {/* The whole app is anonymous — two destinations. */}
            <Route path="/" element={<HomePage />} />
            <Route path="/decouvrir" element={<DecouvrirPage />} />
            <Route path="/a-vous-de-jouer" element={<AVousDeJouerPage />} />
            <Route path="/playground" element={<PlaygroundPage />} />
            <Route path="/laboratoire" element={<LaboratoirePage />} />

            {/* Retired routes — the table lives in routes.ts, which the e2e
                suite reads too, so a redirect can never go untested. */}
            {Object.entries(LEGACY_REDIRECTS).map(([from, to]) => (
              <Route key={from} path={from} element={<Navigate to={to} replace />} />
            ))}

            {/* Catch-all 404 — unknown / removed routes */}
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </Suspense>
      </ErrorBoundary>

      {/* PWA update toast */}
      <UpdatePrompt />
    </div>
  );
};

const App: React.FC = () => (
  <ElectionProvider>
    <ToastProvider>
      <Router>
        <AppContent />
      </Router>
    </ToastProvider>
  </ElectionProvider>
);

export default App;
