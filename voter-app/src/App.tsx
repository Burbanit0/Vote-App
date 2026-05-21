import React from 'react';
import { BrowserRouter as Router, Route, Routes, useLocation, Navigate } from 'react-router';

import Navbar from './components/Navbar';
import ErrorBoundary from './components/Route/ErrorBoundary';
import { TeacherBanner, TeacherCaptureButton } from './components/teacher/TeacherBanner';

import HomePage from './pages/HomePage';
import SimulationPage from './pages/SimulationPage';
import SimulationComparePage from './pages/SimulationComparePage';
import ScenarioBuilderPage from './pages/ScenarioBuilderPage';
import ConstitutionalCrisisPage from './pages/ConstitutionalCrisisPage';
import QuizPage from './pages/QuizPage';
import WhatIfPage from './pages/WhatIfPage';
import CampaignSimulatorPage from './pages/CampaignSimulatorPage';
import BlankContagionPage from './pages/BlankContagionPage';
import InternationalRegimesPage from './pages/InternationalRegimesPage';
import ApiDocsPage from './pages/ApiDocsPage';
import ScenarioGalleryPage from './pages/ScenarioGalleryPage';
import TeacherPresentationPage from './pages/TeacherPresentationPage';
import ElectionLabPage from './pages/ElectionLabPage';
import QuadraticFundingPage from './pages/QuadraticFundingPage';
import TechDemocracyPage from './pages/TechDemocracyPage';
import SortitionPage from './pages/SortitionPage';
import Login from './pages/Login';
import OAuthCallback from './pages/OAuthCallback';
import Register from './pages/Register';
import ProfilePage from './pages/ProfilePage';
import UserProfilePage from './pages/UserProfilePage';

import { useAuth } from './context/AuthContext';
import AuthGuard from './context/AuthGuard';
import { ThemeProvider, useTheme } from './context/ThemeContext';
import { ExpertModeProvider } from './context/ExpertModeContext';
import { ToastProvider } from './components/shared/ToastNotification';
import { ElectionProvider } from './context/ElectionContext';
import UpdatePrompt from './components/shared/UpdatePrompt';
import OfflineBanner from './components/shared/OfflineBanner';
import { TeacherModeProvider } from './context/TeacherModeContext';

import 'bootstrap/dist/css/bootstrap.min.css';

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
        <Routes>
          {/* Auth routes */}
          <Route path="/login"         element={!user ? <Login />         : <Navigate to="/" />} />
          <Route path="/register"      element={!user ? <Register />      : <Navigate to="/" />} />
          <Route path="/oauth/callback" element={<OAuthCallback />} />

          {/* Public routes — accessible without account */}
          <Route path="/"                      element={<HomePage />} />
          <Route path="/scenario-builder"      element={<AuthGuard component={ScenarioBuilderPage}      requireAuth={false} />} />
          <Route path="/simulation/compare"    element={<AuthGuard component={SimulationComparePage}   requireAuth={false} />} />
          <Route path="/constitutional-crisis" element={<AuthGuard component={ConstitutionalCrisisPage} requireAuth={false} />} />
          <Route path="/quiz"                  element={<QuizPage />} />
          <Route path="/what-if"              element={<WhatIfPage />} />
          <Route path="/campaign"             element={<CampaignSimulatorPage />} />
          <Route path="/blank-contagion"      element={<BlankContagionPage />} />
          <Route path="/regimes-internationaux" element={<InternationalRegimesPage />} />
          <Route path="/api-docs"              element={<ApiDocsPage />} />
          <Route path="/teacher/presentation" element={<TeacherPresentationPage />} />
          <Route path="/election-lab"         element={<ElectionLabPage />} />
          <Route path="/quadratic-funding" element={<QuadraticFundingPage />} />
          <Route path="/tech-democracy"   element={<TechDemocracyPage />} />
          <Route path="/sortition"        element={<SortitionPage />} />

          {/* Auth-protected routes */}
          <Route path="/profile"    element={<AuthGuard component={ProfilePage} />} />
          <Route path="users/:id"   element={<AuthGuard component={UserProfilePage} />} />
          <Route path="/simulation" element={<AuthGuard component={SimulationPage} />} />
        </Routes>
      </ErrorBoundary>

      {/* Floating capture button — visible only when teacher mode is active */}
      <TeacherCaptureButton />

      {/* PWA update toast */}
      <UpdatePrompt />
    </div>
  );
};

const App: React.FC = () => (
  <ThemeProvider>
    <ExpertModeProvider>
      <ElectionProvider>
        <TeacherModeProvider>
          <ToastProvider>
            <Router>
              <AppContent />
            </Router>
          </ToastProvider>
        </TeacherModeProvider>
      </ElectionProvider>
    </ExpertModeProvider>
  </ThemeProvider>
);

export default App;
