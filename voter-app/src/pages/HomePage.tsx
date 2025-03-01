// src/pages/HomePage.tsx
import React from 'react';
import { Link } from 'react-router-dom';

const HomePage: React.FC = () => {
  return (
    <div>
      <h1>Welcome to the Voting System</h1>
      <p>Use the navigation links to manage candidates, voters, cast votes, and view results.</p>
      <nav>
        <ul>
          <li><Link to="/candidates">Manage Candidates</Link></li>
          <li><Link to="/voters">Manage Voters</Link></li>
          <li><Link to="/vote">Cast Your Vote</Link></li>
          <li><Link to="/results">View Results</Link></li>
        </ul>
      </nav>
    </div>
  );
};

export default HomePage;
