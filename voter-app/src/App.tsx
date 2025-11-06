import React from 'react';
import { BrowserRouter as Router, Route, Routes, useLocation, Navigate } from 'react-router';

import Navbar from './components/Navbar';
import ElectionForm from './components/Election/ElectionForm';
import ErrorBoundary from './components/Route/ErrorBoundary';

import HomePage from './pages/HomePage';
import SimulationPage from './pages/SimulationPage';
import ElectionDetail from './pages/ElectionDetailPage';
import Login from './pages/Login';
import Register from './pages/Register';
import ProfilePage from './pages/ProfilePage';
import UserProfilePage from './pages/UserProfilePage';
import PartyPage from './pages/PartyPage';
import PartyDetailPage from './pages/PartyDetailPage';

import { useAuth } from './context/AuthContext';
import AuthGuard from './context/AuthGuard';

import 'bootstrap/dist/css/bootstrap.min.css';

const AppContent: React.FC = () => {
  const location = useLocation();
  const { user } = useAuth();

  // Hide the Navbar on the Home page
  const shouldShowNavbar =  ['/login', '/register'];

  return (
    <div className="App">
      { !shouldShowNavbar.includes(location.pathname) && <Navbar />}
      <ErrorBoundary>
        <Routes>

          <Route path="/login" element={!user ? <Login /> : <Navigate to="/" />} />
          <Route path="/register" element={!user ? <Register /> : <Navigate to="/" />} />

          <Route path="/" element={<AuthGuard component={HomePage} />} />

          <Route path="/create_election" element={<AuthGuard component={ElectionForm}/> } />
          <Route path="/elections/:id" element={<AuthGuard component={ElectionDetail}/> } />

          <Route path="/profile" element={<AuthGuard component={ProfilePage} />} />
          <Route path="users/:id" element={<AuthGuard component={UserProfilePage}/>} />
          
          <Route path="/parties" element={<AuthGuard component={PartyPage} />} />
          <Route path="/parties/:party_id" element={<AuthGuard component={PartyDetailPage} />} />
          <Route path="/simulation" element={<AuthGuard component={SimulationPage} />} />
          
        </Routes>
      </ErrorBoundary>
    </div>
  );
};

const App: React.FC = () => {
  return (
        <Router>
          <AppContent />
        </Router>
  );
};

export default App;
