// src/pages/SimulationPage.tsx

import React, { useState } from 'react';
import { Container, Alert } from 'react-bootstrap';
import SimulationForm from '../components/Simulation/SimulationForm';
import SimulationResult from '../components/Simulation/SimulationResult';
import { simulateVote } from '../services/';
const SimulateVotesPage: React.FC = () => {
    const [numVoters, setNumVoters] = useState(10);
    const [numCandidates, setNumCandidates] = useState(3);
    const [result, setResult] = useState<{ votes: any[]; condorcet_winner: any; two_round_winner: any } | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
  
    const simulateVotes = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await simulateVote(numVoters, numCandidates);
        setResult(response);
      } catch (error) {
        setError('Failed to simulate votes. Please try again.');
      } finally {
        setLoading(false);
      }
    };
  
    return (
      <Container>
        <h2 className="my-4">Simulate Votes</h2>
        <SimulationForm
          numVoters={numVoters}
          setNumVoters={setNumVoters}
          numCandidates={numCandidates}
          setNumCandidates={setNumCandidates}
          simulateVotes={simulateVotes}
          loading={loading}
        />
        {error && <Alert variant="danger" className="mt-3">{error}</Alert>}
        <SimulationResult result={result} />
      </Container>
    );
  };
  
  export default SimulateVotesPage;