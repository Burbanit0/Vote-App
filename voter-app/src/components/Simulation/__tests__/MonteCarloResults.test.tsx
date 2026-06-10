import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import MonteCarloResults from '../MonteCarloResults';

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  BarChart: ({ children }: any) => <div>{children}</div>,
  Bar: ({ children }: any) => <div>{children}</div>,
  CartesianGrid: () => <div />,
  Cell: () => <div />,
  ErrorBar: () => <div />,
  Tooltip: () => <div />,
  XAxis: () => <div />,
  YAxis: () => <div />,
}));

vi.mock('../../shared/ResponsiveTable', () => ({
  default: ({ children, className }: any) => <div className={className}>{children}</div>,
}));
vi.mock('../../shared/SkeletonCard', () => ({
  default: ({ height }: any) => <div style={{ height }} />,
}));
vi.mock('../../../hooks/useChartTheme', () => ({
  useChartTheme: () => ({
    isDark: false,
    gridStroke: '#e0e0e0',
    tickFill: '#333',
    tooltipStyle: {},
  }),
}));
vi.mock('../../../services/simulationCompareApi', () => ({
  getMonteCarlo: vi.fn(),
}));
vi.mock('../../../hooks/useMonteCarloStream', () => ({
  useMonteCarloStream: () => ({
    progress: 0,
    iteration: 0,
    total: 0,
    condorcetRate: 0,
    partialResults: {},
    isRunning: false,
    complete: null,
    error: null,
    regretHistory: {},
    agreementHistory: [],
    ciHalfLatest: {},
    iterationCheckpoints: [],
    start: vi.fn(),
    stop: vi.fn(),
    reset: vi.fn(),
  }),
}));
vi.mock('../MonteCarloLiveChart', () => ({ default: () => null }));
vi.mock('../MonteCarloConvergencePanel', () => ({ default: () => null }));

describe('MonteCarloResults', () => {
  it('renders config form and initial prompt', () => {
    render(<MonteCarloResults baseParams={{}} />);
    expect(screen.getByRole('button', { name: /Run Monte Carlo/ })).toBeInTheDocument();
    expect(screen.getByText(/Monte Carlo Configuration/)).toBeInTheDocument();
  });

  it('renders results when getMonteCarlo resolves (standard mode)', async () => {
    const { getMonteCarlo } = await import('../../../services/simulationCompareApi');
    (getMonteCarlo as jest.Mock).mockResolvedValue({
      num_runs: 50,
      num_voters_per_run: 200,
      condorcet_winner_exists_rate: 0.75,
      config: {},
      methods: {
        plurality: {
          winner_distribution: { Alice: 0.6, Bob: 0.4 },
          most_common_winner: 'Alice',
          winner_stability: 0.2,
          condorcet_compliance_rate: 0.9,
          bayesian_regret_mean: 0.1,
          bayesian_regret_std: 0.05,
          bayesian_regret_ci_95: [0.05, 0.15],
          majority_satisfaction_mean: 0.8,
          majority_satisfaction_ci_95: [0.7, 0.9],
        },
      },
      inter_method_agreement: { 'plurality|plurality': 1 },
    });

    render(<MonteCarloResults baseParams={{}} />);

    // Disable streaming to use the HTTP path
    const streamingToggle = screen.getByRole('checkbox', {
      name: /Real-time streaming|Streaming temps réel/i,
    });
    fireEvent.click(streamingToggle);

    fireEvent.click(screen.getByRole('button', { name: /Run Monte Carlo/ }));
    expect(await screen.findByText(/Condorcet winner in/)).toBeInTheDocument();
  });
});
