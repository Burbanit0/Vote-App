import React, { Suspense } from 'react';
import {
  BrowserRouter as Router,
  Route,
  Routes,
  Navigate,
  useLocation,
  useNavigationType,
} from 'react-router';
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
const PolityPage = React.lazy(() => import('./pages/PolityPage'));
const NotFoundPage = React.lazy(() => import('./pages/NotFoundPage'));

import { useTheme } from './stores/useUIStore';
import { ElectionProvider } from './stores/useElectionStore';
import UpdatePrompt from './components/shared/ui/UpdatePrompt';
import OfflineBanner from './components/shared/ui/OfflineBanner';

import './styles/tailwind.css';

const RouteFallback: React.FC = () => (
  <div className="flex justify-center items-center py-5" data-testid="route-fallback">
    <Spinner role="status" size="sm" className="me-2" />
    <span className="text-muted-foreground text-sm">Chargement…</span>
  </div>
);

// <BrowserRouter> restores no scroll position: a <Link> to another page kept the old
// offset, so a phone tapping a story at the bottom of /decouvrir landed mid-page,
// far from the story. Reset on a path change; back/forward (POP) keeps the browser's.
export const ScrollToTop: React.FC = () => {
  const { pathname } = useLocation();
  const navType = useNavigationType();
  React.useEffect(() => {
    if (navType !== 'POP') window.scrollTo(0, 0);
    // Keyed on the path alone: a replace that keeps the path (a Lab fiche chip, the
    // Polity tick slider writing the query) changes navType and must not jump.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);
  return null;
};

const AppContent: React.FC = () => {
  const { theme } = useTheme();

  return (
    <div className="App" data-bs-theme={theme}>
      <ScrollToTop />
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
            <Route path="/polity" element={<PolityPage />} />

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
    <Router>
      <AppContent />
    </Router>
  </ElectionProvider>
);

export default App;
