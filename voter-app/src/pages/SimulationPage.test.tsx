import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import SimulationPage from './SimulationPage';
import { simulateVote } from '../services/simulationsApi';

vi.mock('../services/simulationsApi', () => ({
  simulateVote: vi.fn(),
}));

vi.mock('../components/Simulation/SimulationForm', () => {
  return { default: function MockForm({
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
  } };
});

vi.mock('../components/Simulation/SimulationResult', () => {
  return { default: function MockResult({ result }: { result: any }) {
    return (
      <div data-testid="simulation-result">
        {result ? 'Résultats chargés' : 'Aucun résultat'}
      </div>
    );
  } };
});

vi.mock('../components/Simulation/VoterVisualization', () => {
  return { default: function MockVoterVis() {
    return <div data-testid="voter-vis">VoterVis</div>;
  } };
});

vi.mock('../components/Simulation/CandidatesVisualization', () => {
  return { default: function MockCandVis() {
    return <div data-testid="candidate-vis">CandidateVis</div>;
  } };
});

vi.mock('../components/Simulation/UtilityVisualization', () => {
  return { default: function MockUtilVis() {
    return <div data-testid="utility-vis">UtilityVis</div>;
  } };
});

describe('SimulationPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
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
