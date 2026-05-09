import React from 'react';
import { BrowserRouter as Router, Route, Routes, useLocation, Navigate } from 'react-router';

import Navbar from './components/Navbar';
import ErrorBoundary from './components/Route/ErrorBoundary';

import HomePage from './pages/HomePage';
import SimulationPage from './pages/SimulationPage';
import SimulationComparePage from './pages/SimulationComparePage';
import ScenarioBuilderPage from './pages/ScenarioBuilderPage';
import ConstitutionalCrisisPage from './pages/ConstitutionalCrisisPage';
import Login from './pages/Login';
import Register from './pages/Register';
import ProfilePage from './pages/ProfilePage';
import UserProfilePage from './pages/UserProfilePage';

import { useAuth } from './context/AuthContext';
import AuthGuard from './context/AuthGuard';
import { ThemeProvider, useTheme } from './context/ThemeContext';
import { ToastProvider } from './components/shared/ToastNotification';

import 'bootstrap/dist/css/bootstrap.min.css';

const AppContent: React.FC = () => {
  const location = useLocation();
  const { user } = useAuth();
  const { theme } = useTheme();

  const shouldHideNavbar = ['/login', '/register'];

  return (
    <div className="App" data-bs-theme={theme}>
      {!shouldHideNavbar.includes(location.pathname) && <Navbar />}
      <ErrorBoundary>
        <Routes>
          {/* Auth routes */}
          <Route path="/login"    element={!user ? <Login />    : <Navigate to="/" />} />
          <Route path="/register" element={!user ? <Register /> : <Navigate to="/" />} />

          {/* Public routes — accessible without account */}
          <Route path="/"                      element={<HomePage />} />
          <Route path="/scenario-builder"      element={<AuthGuard component={ScenarioBuilderPage}      requireAuth={false} />} />
          <Route path="/simulation/compare"    element={<AuthGuard component={SimulationComparePage}   requireAuth={false} />} />
          <Route path="/constitutional-crisis" element={<AuthGuard component={ConstitutionalCrisisPage} requireAuth={false} />} />

          {/* Auth-protected routes */}
          <Route path="/profile"    element={<AuthGuard component={ProfilePage} />} />
          <Route path="users/:id"   element={<AuthGuard component={UserProfilePage} />} />
          <Route path="/simulation" element={<AuthGuard component={SimulationPage} />} />
        </Routes>
      </ErrorBoundary>
    </div>
  );
};

const App: React.FC = () => (
  <ThemeProvider>
    <ToastProvider>
      <Router>
        <AppContent />
      </Router>
    </ToastProvider>
  </ThemeProvider>
);

export default App;
