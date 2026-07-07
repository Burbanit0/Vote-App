import React, { Suspense } from 'react';
import { BrowserRouter as Router, Route, Routes, useLocation, Navigate } from 'react-router';
import { Spinner } from '@/components/ui/spinner';

import Navbar from './components/Navbar';
import ErrorBoundary from './components/Route/ErrorBoundary';
import { TeacherBanner, TeacherCaptureButton } from './components/teacher/TeacherBanner';

// ── Eager imports — small, on the critical first-paint path ─────────────────
import HomePage from './pages/HomePage';
import Login from './pages/Login';
import Register from './pages/Register';
import OAuthCallback from './pages/OAuthCallback';

// ── Lazy imports — heavier pages, code-split into separate chunks so the
//    HomePage download doesn't drag in everything (Lab, Theory, Simulator,
//    etc.). Each becomes its own chunk under build/assets/.
const SimulationPage = React.lazy(() => import('./pages/SimulationPage'));
const SimulationComparePage = React.lazy(() => import('./pages/SimulationComparePage'));
const ScenarioBuilderPage = React.lazy(() => import('./pages/ScenarioBuilderPage'));
const TeacherPresentationPage = React.lazy(() => import('./pages/TeacherPresentationPage'));
const PlaygroundPage = React.lazy(() => import('./pages/PlaygroundPage'));
const ScenarioGalleryPage = React.lazy(() => import('./pages/ScenarioGalleryPage'));
const LaboratoirePage = React.lazy(() => import('./pages/LaboratoirePage'));
const NotFoundPage = React.lazy(() => import('./pages/NotFoundPage'));
const ProfilePage = React.lazy(() => import('./pages/ProfilePage'));
const UserProfilePage = React.lazy(() => import('./pages/UserProfilePage'));

import { useAuth } from './stores/useAuthStore';
import AuthGuard from './components/Route/AuthGuard';
import { useTheme } from './stores/useUIStore';
import { ToastProvider } from './components/shared/ToastNotification';
import { ElectionProvider } from './stores/useElectionStore';
import UpdatePrompt from './components/shared/UpdatePrompt';
import OfflineBanner from './components/shared/OfflineBanner';

// Tailwind v4 (no preflight) + Bootstrap — both imported via styles/tailwind.css,
// which loads Bootstrap into a lower cascade layer so Tailwind utilities win
// collisions on migrated components. (Bootstrap CSS used to be imported here.)
import './styles/tailwind.css';

const RouteFallback: React.FC = () => (
  <div className="flex justify-center items-center py-5" data-testid="route-fallback">
    <Spinner role="status" size="sm" className="me-2" />
    <span className="text-muted-foreground text-sm">Chargement…</span>
  </div>
);

const AppContent: React.FC = () => {
  const location = useLocation();
  const { user } = useAuth();
  const { theme } = useTheme();

  const shouldHideNavbar = ['/login', '/register'];

  return (
    <div id="teacher-capture-root" className="App" data-bs-theme={theme}>
      <OfflineBanner />
      {!shouldHideNavbar.includes(location.pathname) && (
        <>
          <TeacherBanner />
          <Navbar />
        </>
      )}
      <ErrorBoundary>
        <Suspense fallback={<RouteFallback />}>
          <Routes>
            {/* Auth routes */}
            <Route path="/login" element={!user ? <Login /> : <Navigate to="/" />} />
            <Route path="/register" element={!user ? <Register /> : <Navigate to="/" />} />
            <Route path="/oauth/callback" element={<OAuthCallback />} />

            {/* Public routes — accessible without account */}
            <Route path="/" element={<HomePage />} />
            <Route
              path="/scenario-builder"
              element={<AuthGuard component={ScenarioBuilderPage} requireAuth={false} />}
            />
            <Route
              path="/simulation/compare"
              element={<AuthGuard component={SimulationComparePage} requireAuth={false} />}
            />
            <Route path="/teacher/presentation" element={<TeacherPresentationPage />} />
            <Route path="/playground" element={<PlaygroundPage />} />
            <Route path="/laboratoire" element={<LaboratoirePage />} />
            <Route path="/galerie" element={<ScenarioGalleryPage />} />

            {/* Retired standalone pages — their content now lives in the playground
                (what-if variation) or the laboratoire's anchors (theory, mechanisms,
                systems, régimes). Redirect old/bookmarked links instead of 404-ing. */}
            <Route path="/what-if" element={<Navigate to="/playground" replace />} />
            <Route path="/campagne" element={<Navigate to="/playground" replace />} />
            <Route path="/election-lab" element={<Navigate to="/playground" replace />} />
            <Route path="/sortition" element={<Navigate to="/playground" replace />} />
            <Route path="/party-dynamics" element={<Navigate to="/playground" replace />} />
            <Route path="/theory" element={<Navigate to="/laboratoire" replace />} />
            <Route path="/quiz" element={<Navigate to="/laboratoire" replace />} />
            <Route
              path="/regimes-internationaux"
              element={<Navigate to="/laboratoire" replace />}
            />
            <Route path="/quadratic-funding" element={<Navigate to="/laboratoire" replace />} />
            <Route path="/tech-democracy" element={<Navigate to="/laboratoire" replace />} />
            <Route path="/api-docs" element={<Navigate to="/laboratoire" replace />} />

            {/* Auth-protected routes */}
            <Route path="/profile" element={<AuthGuard component={ProfilePage} />} />
            <Route path="users/:id" element={<AuthGuard component={UserProfilePage} />} />
            <Route path="/simulation" element={<AuthGuard component={SimulationPage} />} />

            {/* Catch-all 404 — unknown / removed routes */}
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </Suspense>
      </ErrorBoundary>

      {/* Floating capture button — visible only when teacher mode is active */}
      <TeacherCaptureButton />

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
