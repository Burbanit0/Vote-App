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
const ConstitutionalCrisisPage = React.lazy(() => import('./pages/ConstitutionalCrisisPage'));
const QuizPage = React.lazy(() => import('./pages/QuizPage'));
const WhatIfPage = React.lazy(() => import('./pages/WhatIfPage'));
const CampaignSimulatorPage = React.lazy(() => import('./pages/CampaignSimulatorPage'));
const BlankContagionPage = React.lazy(() => import('./pages/BlankContagionPage'));
const InternationalRegimesPage = React.lazy(() => import('./pages/InternationalRegimesPage'));
const ApiDocsPage = React.lazy(() => import('./pages/ApiDocsPage'));
const TeacherPresentationPage = React.lazy(() => import('./pages/TeacherPresentationPage'));
const ElectionLabPage = React.lazy(() => import('./pages/ElectionLabPage'));
const QuadraticFundingPage = React.lazy(() => import('./pages/QuadraticFundingPage'));
const TechDemocracyPage = React.lazy(() => import('./pages/TechDemocracyPage'));
const SortitionPage = React.lazy(() => import('./pages/SortitionPage'));
const PartyDynamicsPage = React.lazy(() => import('./pages/PartyDynamicsPage'));
const TheoryPage = React.lazy(() => import('./pages/TheoryPage'));
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
            <Route
              path="/constitutional-crisis"
              element={<AuthGuard component={ConstitutionalCrisisPage} requireAuth={false} />}
            />
            <Route path="/quiz" element={<QuizPage />} />
            <Route path="/what-if" element={<WhatIfPage />} />
            <Route path="/campaign" element={<CampaignSimulatorPage />} />
            <Route path="/blank-contagion" element={<BlankContagionPage />} />
            <Route path="/regimes-internationaux" element={<InternationalRegimesPage />} />
            <Route path="/api-docs" element={<ApiDocsPage />} />
            <Route path="/teacher/presentation" element={<TeacherPresentationPage />} />
            <Route path="/election-lab" element={<ElectionLabPage />} />
            <Route path="/quadratic-funding" element={<QuadraticFundingPage />} />
            <Route path="/tech-democracy" element={<TechDemocracyPage />} />
            <Route path="/sortition" element={<SortitionPage />} />
            <Route path="/party-dynamics" element={<PartyDynamicsPage />} />
            <Route path="/theory" element={<TheoryPage />} />

            {/* Auth-protected routes */}
            <Route path="/profile" element={<AuthGuard component={ProfilePage} />} />
            <Route path="users/:id" element={<AuthGuard component={UserProfilePage} />} />
            <Route path="/simulation" element={<AuthGuard component={SimulationPage} />} />
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
