import React from 'react';
import { Form, Button, Spinner } from 'react-bootstrap';

interface SimulationFormProps {
  numVoters: number;
  setNumVoters: (value: number) => void;
  numCandidates: number;
  setNumCandidates: (value: number) => void;
  simulateVotes: () => void;
  loading: boolean;
}

const SimulationForm: React.FC<SimulationFormProps> = ({
  numVoters,
  setNumVoters,
  numCandidates,
  setNumCandidates,
  simulateVotes,
  loading,
}) => {
  return (
    <Form>
      <Form.Group controlId="formNumVoters">
        <Form.Label>Number of Voters:</Form.Label>
        <Form.Control
          type="number"
          value={numVoters}
          onChange={(e) => setNumVoters(Number(e.target.value))}
        />
      </Form.Group>
      <Form.Group controlId="formNumCandidates">
        <Form.Label>Number of Candidates:</Form.Label>
        <Form.Control
          type="number"
          value={numCandidates}
          onChange={(e) => setNumCandidates(Number(e.target.value))}
        />
      </Form.Group>
      <Button variant="primary" onClick={simulateVotes} disabled={loading}>
        {loading ? <Spinner animation="border" size="sm" /> : 'Simulate Votes'}
      </Button>
    </Form>
  );
};

export default SimulationForm;