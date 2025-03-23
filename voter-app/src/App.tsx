import React from 'react';
import { BrowserRouter as Router, Route, Routes, useLocation } from 'react-router-dom';
import HomePage from './pages/HomePage';
import CandidatePage from './pages/CandidatePage';
import VoterPage from './pages/VoterPage';
import VotePage from './pages/VotePage';
import ResultsPage from './pages/ResultsPage';
import Navbar from './components/Navbar';
import Profile from './components/Voter/Profile';
import SimulationPage from './pages/SimulationPage';
import Login from './pages/Login';
import Register from './pages/Register';
import AuthGuard from './context/AuthGuard';
import ErrorBoundary from './components/Route/ErrorBoundary';
import 'bootstrap/dist/css/bootstrap.min.css';

const AppContent: React.FC = () => {
  const location = useLocation();

  // Hide the Navbar on the Home page
  const shouldShowNavbar =  ['/', '/login', '/register'];

  return (
    <div className="App">
      { !shouldShowNavbar.includes(location.pathname) && <Navbar />}
      <ErrorBoundary>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/" element={<AuthGuard component={HomePage} />} />
          <Route path="/candidates" element={<AuthGuard component={CandidatePage} role="Admin" />} />
          <Route path="/voters" element={<AuthGuard component={VoterPage} role="Admin" />} />
          <Route path="/vote" element={<AuthGuard component={VotePage} role="Voter" />} />
          <Route path="/results" element={<AuthGuard component={ResultsPage} />} />
          <Route path="/profile" element={<AuthGuard component={Profile} />} />
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
