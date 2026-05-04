import React from 'react';
import { BrowserRouter as Router, Route, Routes, useLocation, Navigate } from 'react-router';

import Navbar from './components/Navbar';
import ErrorBoundary from './components/Route/ErrorBoundary';

import HomePage from './pages/HomePage';
import SimulationPage from './pages/SimulationPage';
import SimulationComparePage from './pages/SimulationComparePage';
import Login from './pages/Login';
import Register from './pages/Register';
import ProfilePage from './pages/ProfilePage';
import UserProfilePage from './pages/UserProfilePage';

import { useAuth } from './context/AuthContext';
import AuthGuard from './context/AuthGuard';

import 'bootstrap/dist/css/bootstrap.min.css';

const AppContent: React.FC = () => {
  const location = useLocation();
  const { user } = useAuth();

  const shouldHideNavbar = ['/login', '/register'];

  return (
    <div className="App">
      {!shouldHideNavbar.includes(location.pathname) && <Navbar />}
      <ErrorBoundary>
        <Routes>
          <Route path="/login" element={!user ? <Login /> : <Navigate to="/" />} />
          <Route path="/register" element={!user ? <Register /> : <Navigate to="/" />} />

          <Route path="/" element={<AuthGuard component={HomePage} />} />
          <Route path="/profile" element={<AuthGuard component={ProfilePage} />} />
          <Route path="users/:id" element={<AuthGuard component={UserProfilePage} />} />
          <Route path="/simulation" element={<AuthGuard component={SimulationPage} />} />
          <Route path="/simulation/compare" element={<AuthGuard component={SimulationComparePage} />} />
        </Routes>
      </ErrorBoundary>
    </div>
  );
};

const App: React.FC = () => (
  <Router>
    <AppContent />
  </Router>
);

export default App;
