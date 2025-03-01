import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const Navbar: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav className="navbar navbar-expand-lg navbar-light bg-light">
      <a className="navbar-brand" href="/">Voting System</a>
      <div className="collapse navbar-collapse" id="navbarNav">
        <ul className="navbar-nav">
          {user && user.role === 'Admin' && (
            <>
              <li className="nav-item"><a className="nav-link" href="/candidates">Candidates</a></li>
              <li className="nav-item"><a className="nav-link" href="/voters">Voters</a></li>
            </>
          )}
          {user && user.role === 'Voter' && (
            <li className="nav-item"><a className="nav-link" href="/vote">Vote</a></li>
          )}
          <li className="nav-item"><a className="nav-link" href="/results">Results</a></li>
          <li className="nav-item">
            {user ? (
              <button className="btn btn-outline-primary" onClick={handleLogout}>Logout</button>
            ) : (
              <button className="btn btn-outline-primary" onClick={() => navigate('/login')}>Login</button>
            )}
          </li>
        </ul>
      </div>
    </nav>
  );
};

export default Navbar;
