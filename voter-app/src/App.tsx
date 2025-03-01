import React from 'react';
import { BrowserRouter as Router, Route, Routes, useLocation } from 'react-router-dom';
import HomePage from './pages/HomePage';
import CandidatePage from './pages/CandidatePage';
import VoterPage from './pages/VoterPage';
import VotePage from './pages/VotePage';
import ResultsPage from './pages/ResultsPage';
import Navbar from './components/Navbar';
import { AuthProvider } from './context/AuthContext';
import Login from './pages/Login';
import Register from './pages/Register';
import AuthGuard from './context/AuthGuard';
import ErrorBoundary from './components/Route/ErrorBoundary';
import 'bootstrap/dist/css/bootstrap.min.css';

const AppContent: React.FC = () => {
  const location = useLocation();

  // Hide the Navbar on the Home page
  const shouldShowNavbar = location.pathname !== '/';

  return (
    <div className="App">
      {shouldShowNavbar && <Navbar />}
      <ErrorBoundary>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/" element={<AuthGuard component={HomePage} />} />
          <Route path="/candidates" element={<AuthGuard component={CandidatePage} role="Admin" />} />
          <Route path="/voters" element={<AuthGuard component={VoterPage} role="Admin" />} />
          <Route path="/vote" element={<AuthGuard component={VotePage} role="Voter" />} />
          <Route path="/results" element={<AuthGuard component={ResultsPage} />} />
        </Routes>
      </ErrorBoundary>
    </div>
  );
};

const App: React.FC = () => {
  return (
    <Router>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </Router>
  );
};

export default App;
