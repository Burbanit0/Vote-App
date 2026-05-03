// src/pages/SimulationPage.tsx

import React, { useState } from 'react';
import { Container, Alert, Tabs, Tab } from 'react-bootstrap';
import SimulationForm, { SimulationFormData } from '../components/Simulation/SimulationForm';
import SimulationResult, { SimulationResponse } from '../components/Simulation/SimulationResult';
import { simulateVote } from '../services';
import VoterVisualization from '../components/Simulation/VoterVisualization';
import CandidatesVisualization from '../components/Simulation/CandidatesVisualization';
import UtilityVisualization from '../components/Simulation/UtilityVisualization';

const SimulateVotesPage: React.FC = () => {
  const [result, setResult] = useState<SimulationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState<SimulationFormData>({
    simulationType: ['votes'],
    populationSize: 1000,
    candidates: ['Alice', 'Bob', 'Charlie'],
    turnoutRate: 0.7,
    demographics: {
      age: { '18-25': 0.2, '26-40': 0.3, '41-60': 0.3, '60+': 0.2 },
      gender: { male: 0.48, female: 0.48, 'non-binary': 0.04 },
      location: { urban: 0.5, suburban: 0.3, rural: 0.2 },
      education: { 'high-school': 0.3, bachelor: 0.4, advanced: 0.3 },
      income: { low: 0.2, middle: 0.6, high: 0.2 },
      ideology: { left: 0.35, center: 0.3, right: 0.35 },
    },
    influenceWeights: {
      location: {
        urban: { Alice: 1.5, Bob: 0.8, Charlie: 1.0 },
        suburban: { Alice: 1.0, Bob: 1.2, Charlie: 0.9 },
        rural: { Alice: 0.7, Bob: 1.3, Charlie: 1.1 },
      },
      income: {
        low: { Alice: 1.2, Bob: 0.9, Charlie: 1.0 },
        middle: { Alice: 1.0, Bob: 1.0, Charlie: 1.0 },
        high: { Alice: 0.8, Bob: 1.3, Charlie: 1.0 },
      },
      ideology: {
        left: { Alice: 2.0, Bob: 0.5, Charlie: 0.8 },
        center: { Alice: 1.0, Bob: 1.0, Charlie: 1.0 },
        right: { Alice: 0.5, Bob: 1.5, Charlie: 1.2 },
      },
    },
  });

  const simulateVotes = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await simulateVote(formData);
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
      <Tabs defaultActiveKey="Form" id="uncontrolled-tab-example" className="mb-3">
        <Tab eventKey="Form" title="Form">
          Tab content for Home
          <SimulationForm
            simulateVotes={simulateVotes}
            loading={loading}
            formData={formData}
            setFormData={setFormData}
          />
          {error && (
            <Alert variant="danger" className="mt-3">
              {error}
            </Alert>
          )}
        </Tab>
        <Tab eventKey="Voters" title="Voters">
          <VoterVisualization />
        </Tab>
        <Tab eventKey="Candidates" title="Candidates">
          <CandidatesVisualization />
        </Tab>
        <Tab eventKey="Utility" title="Utility">
          <UtilityVisualization />
        </Tab>
        <Tab eventKey="Result" title="Result">
          <SimulationResult result={result} />
        </Tab>
      </Tabs>
    </Container>
  );
};

export default SimulateVotesPage;
