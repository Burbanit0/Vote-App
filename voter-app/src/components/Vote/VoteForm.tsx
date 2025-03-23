import React, { useEffect, useState } from 'react';
import { Button, Form, Container, Alert } from 'react-bootstrap';
import { fetchCandidates, castVote } from '../../services/api'; // Adjust the import path as needed
import { Candidate } from '../../types';
import { useAuth } from '../../context/AuthContext';
import { AxiosError } from 'axios';

const VotingForm: React.FC = () => {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [preferences, setPreferences] = useState<{ [key: number]: number }>({});
  const { user } = useAuth(); // Assume user is fetched from context or props
  const [error, setError] = useState<string | null>(null);

  interface ApiErrorResponse {
    msg: string;
  }

  useEffect(() => {
    const loadCandidates = async () => {
      try {
        const candidatesData = await fetchCandidates();
        setCandidates(candidatesData);
      } catch (error) {
        console.error('Failed to fetch candidates:', error);
      }
    };

    loadCandidates();
  }, []);

  const handlePreferenceChange = (candidateId: number, rank: number) => {
    // Check if the rank is already assigned to another candidate
    const isRankTaken = Object.values(preferences).includes(rank);

    if (isRankTaken && preferences[candidateId] !== rank) {
      setError(`Rank ${rank} is already assigned to another candidate.`);
    } else {
      setError(null);
      setPreferences((prevPreferences) => ({
        ...prevPreferences,
        [candidateId]: rank,
      }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    // Check if all candidates have unique ranks
    const assignedRanks = Object.values(preferences);
    const uniqueRanks = new Set(assignedRanks);

    if (uniqueRanks.size !== candidates.length || assignedRanks.some(rank => rank < 1 || rank > candidates.length)) {
      setError('Please assign a unique rank between 1 and ' + candidates.length + ' to each candidate.');
      return;
    }

    for (const candidateId in preferences) {
      const rank = preferences[candidateId];
      if (rank !== undefined && user?.voter?.id !== undefined) {
        try {
          await castVote({
            candidate_id: parseInt(candidateId),
            voter_id: user.voter.id,
            vote_type: 'ordered',
            rank: rank,
            vote_id: 0,
            weight: 0,
            rating: 0
          });
        } catch (error) {
          const axiosError = error as AxiosError<ApiErrorResponse>;
          setError(axiosError.response?.data?.msg || 'Failed to cast vote. Please try again.');
          return;
        }
      }
    }

    // Optionally, clear the form or show a success message
    setPreferences({});
    setError('Votes submitted successfully!');
  };

  return (
    <Container>
      <h2>Vote for Candidates</h2>
      {error && <Alert variant="danger">{error}</Alert>}
      <Form onSubmit={handleSubmit}>
        {candidates.map((candidate) => (
          <Form.Group key={candidate.id}>
            <Form.Label>{candidate.first_name} {candidate.last_name}</Form.Label>
            <Form.Control
              type="number"
              min={1}
              max={candidates.length}
              value={preferences[candidate.id] || ''}
              onChange={(e) => handlePreferenceChange(candidate.id, Number(e.target.value))}
            />
          </Form.Group>
        ))}
        <Button type="submit">Submit Votes</Button>
      </Form>
    </Container>
  );
};

export default VotingForm;