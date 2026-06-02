import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { act } from 'react';
import BandwagonAnalysis from '../BandwagonAnalysis';
import { getBandwagonAnalysis } from '../../../services/simulationCompareApi';
import { BandwagonResult } from '../../../types';

vi.mock('../../../services/simulationCompareApi', () => ({
  getBandwagonAnalysis: vi.fn(),
}));

vi.mock('../../../hooks/useChartTheme', () => ({
  useChartTheme: () => ({
    isDark: false,
    gridStroke: '#e0e0e0',
    tickFill: '#666',
    tooltipStyle: {},
    refStroke: '#ccc',
  }),
}));

const mockResult: BandwagonResult = {
  num_rounds: 3,
  influence_strength: 0.3,
  convergence_round: 2,
  rounds: [
    {
      round: 0,
      poll_standings: { Alice: 0.5, Bob: 0.3, Carol: 0.2 },
      methods: {
        plurality: { winner: 'Alice', bayesian_regret: 0.05 },
        irv: { winner: 'Alice', bayesian_regret: 0.03 },
      },
      voter_lean_distribution: { mean: 0.5, std: 0.2, polarization_index: 0.3 },
    },
    {
      round: 1,
      poll_standings: { Alice: 0.55, Bob: 0.25, Carol: 0.2 },
      methods: {
        plurality: { winner: 'Alice', bayesian_regret: 0.06 },
        irv: { winner: 'Alice', bayesian_regret: 0.04 },
      },
      voter_lean_distribution: { mean: 0.52, std: 0.18, polarization_index: 0.28 },
    },
    {
      round: 2,
      poll_standings: { Alice: 0.6, Bob: 0.2, Carol: 0.2 },
      methods: {
        plurality: { winner: 'Alice', bayesian_regret: 0.07 },
        irv: { winner: 'Alice', bayesian_regret: 0.05 },
      },
      voter_lean_distribution: { mean: 0.55, std: 0.15, polarization_index: 0.25 },
    },
  ],
  amplification_by_method: {
    plurality: 0.05,
    irv: 0.02,
  },
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe('BandwagonAnalysis', () => {
  it('renders input controls', () => {
    render(<BandwagonAnalysis baseParams={{}} />);
    expect(screen.getByText(/Bandwagon simulation settings/)).toBeInTheDocument();
    expect(screen.getAllByText(/Influence strength/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole('button', { name: /Run/ })).toBeInTheDocument();
  });

  it('shows info alert before running simulation', () => {
    render(<BandwagonAnalysis baseParams={{}} />);
    expect(screen.getByText(/Adjust the parameters/)).toBeInTheDocument();
  });

  it('renders convergence alert when simulation completes', async () => {
    (getBandwagonAnalysis as jest.Mock).mockResolvedValue(mockResult);

    render(<BandwagonAnalysis baseParams={{}} />);

    const launchButton = screen.getByRole('button', { name: /Run/ });
    await act(async () => {
      launchButton.click();
    });

    await waitFor(() => {
      expect(screen.getByText(/stabilized at round/)).toBeInTheDocument();
    });
  });

  it('renders poll chart and regret chart after simulation', async () => {
    (getBandwagonAnalysis as jest.Mock).mockResolvedValue(mockResult);

    render(<BandwagonAnalysis baseParams={{}} />);

    const launchButton = screen.getByRole('button', { name: /Run/ });
    await act(async () => {
      launchButton.click();
    });

    await waitFor(() => {
      expect(screen.getByText(/Poll standings evolution/)).toBeInTheDocument();
      expect(screen.getByText(/Bayesian regret per round/)).toBeInTheDocument();
    });
  });

  it('renders amplification summary table', async () => {
    (getBandwagonAnalysis as jest.Mock).mockResolvedValue(mockResult);

    render(<BandwagonAnalysis baseParams={{}} />);

    const launchButton = screen.getByRole('button', { name: /Run/ });
    await act(async () => {
      launchButton.click();
    });

    await waitFor(() => {
      expect(screen.getByText(/Resistance summary/)).toBeInTheDocument();
      expect(screen.getByText(/Amplification/)).toBeInTheDocument();
    });
  });

  it('renders method labels in amplification table', async () => {
    (getBandwagonAnalysis as jest.Mock).mockResolvedValue(mockResult);

    render(<BandwagonAnalysis baseParams={{}} />);

    const launchButton = screen.getByRole('button', { name: /Run/ });
    await act(async () => {
      launchButton.click();
    });

    await waitFor(() => {
      expect(screen.getByText('Plurality')).toBeInTheDocument();
      expect(screen.getByText('IRV')).toBeInTheDocument();
    });
  });

  it('displays non-convergence warning when convergence_round is null', async () => {
    const noConvergence: BandwagonResult = {
      ...mockResult,
      convergence_round: null,
    };
    (getBandwagonAnalysis as jest.Mock).mockResolvedValue(noConvergence);

    render(<BandwagonAnalysis baseParams={{}} />);

    const launchButton = screen.getByRole('button', { name: /Run/ });
    await act(async () => {
      launchButton.click();
    });

    await waitFor(() => {
      expect(screen.getByText(/No plurality winner convergence/)).toBeInTheDocument();
    });
  });

  it('displays error alert when API call fails', async () => {
    (getBandwagonAnalysis as jest.Mock).mockRejectedValue(new Error('API error'));

    render(<BandwagonAnalysis baseParams={{}} />);

    const launchButton = screen.getByRole('button', { name: /Run/ });
    await act(async () => {
      launchButton.click();
    });

    await waitFor(() => {
      expect(screen.getByText(/Bandwagon simulation failed/)).toBeInTheDocument();
    });
  });
});
