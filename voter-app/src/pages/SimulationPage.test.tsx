import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import SimulationPage from './SimulationPage';
import { simulateVote } from '../services/simulationsApi';

jest.mock('../services/simulationsApi', () => ({
  simulateVote: jest.fn(),
}));

jest.mock('../components/Simulation/SimulationForm', () => {
  return function MockForm({
    simulateVotes,
    loading,
  }: {
    simulateVotes: () => void;
    loading: boolean;
  }) {
    return (
      <div>
        <button data-testid="simulate-btn" onClick={simulateVotes} disabled={loading}>
          {loading ? 'Chargement...' : 'Lancer'}
        </button>
      </div>
    );
  };
});

jest.mock('../components/Simulation/SimulationResult', () => {
  return function MockResult({ result }: { result: any }) {
    return (
      <div data-testid="simulation-result">
        {result ? 'Résultats chargés' : 'Aucun résultat'}
      </div>
    );
  };
});

jest.mock('../components/Simulation/VoterVisualization', () => {
  return function MockVoterVis() {
    return <div data-testid="voter-vis">VoterVis</div>;
  };
});

jest.mock('../components/Simulation/CandidatesVisualization', () => {
  return function MockCandVis() {
    return <div data-testid="candidate-vis">CandidateVis</div>;
  };
});

jest.mock('../components/Simulation/UtilityVisualization', () => {
  return function MockUtilVis() {
    return <div data-testid="utility-vis">UtilityVis</div>;
  };
});

describe('SimulationPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders the simulation form on initial load', () => {
    render(<SimulationPage />);
    expect(screen.getByTestId('simulate-btn')).toBeInTheDocument();
    expect(screen.getByText('Simulate votes')).toBeInTheDocument();
  });

  it('calls simulateVote when the form is submitted', async () => {
    (simulateVote as jest.Mock).mockResolvedValue({ tally: { Alice: 50, Bob: 30 } });
    render(<SimulationPage />);

    fireEvent.click(screen.getByTestId('simulate-btn'));

    await waitFor(() => {
      expect(simulateVote).toHaveBeenCalledTimes(1);
    });
  });

  it('shows results after successful simulation', async () => {
    const mockResult = {
      tally: { Alice: 60, Bob: 40 },
      simulation_type: 'votes',
    };
    (simulateVote as jest.Mock).mockResolvedValue(mockResult);
    render(<SimulationPage />);

    fireEvent.click(screen.getByTestId('simulate-btn'));

    await waitFor(() => {
      expect(screen.getByText('Résultats chargés')).toBeInTheDocument();
    });
  });

  it('shows error alert when simulation fails', async () => {
    (simulateVote as jest.Mock).mockRejectedValue(new Error('Network error'));
    render(<SimulationPage />);

    fireEvent.click(screen.getByTestId('simulate-btn'));

    await waitFor(() => {
      expect(
        screen.getByText('Simulation failed. Please try again.')
      ).toBeInTheDocument();
    });
  });
});
