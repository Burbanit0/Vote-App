import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import MonteCarloResults from '../MonteCarloResults';

jest.mock('recharts', () => ({
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

jest.mock('../../shared/ResponsiveTable', () => ({ children, className }: any) => <div className={className}>{children}</div>);
jest.mock('../../shared/SkeletonCard', () => ({ height }: any) => <div style={{ height }} />);
jest.mock('../../../hooks/useChartTheme', () => ({
  useChartTheme: () => ({
    isDark: false,
    gridStroke: '#e0e0e0',
    tickFill: '#333',
    tooltipStyle: {},
  }),
}));
jest.mock('../../../services/simulationCompareApi', () => ({
  getMonteCarlo: jest.fn(),
}));

describe('MonteCarloResults', () => {
  it('renders config form and initial prompt', () => {
    render(<MonteCarloResults baseParams={{}} />);
    expect(screen.getByRole('button', { name: /Lancer Monte Carlo/ })).toBeInTheDocument();
    expect(screen.getByText(/Configuration Monte Carlo/)).toBeInTheDocument();
  });

  it('renders results when getMonteCarlo resolves', async () => {
    const { getMonteCarlo } = jest.requireMock('../../../services/simulationCompareApi');
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
    fireEvent.click(screen.getByRole('button', { name: /Lancer Monte Carlo/ }));

    expect(await screen.findByText(/Condorcet dans/)).toBeInTheDocument();
  });
});
