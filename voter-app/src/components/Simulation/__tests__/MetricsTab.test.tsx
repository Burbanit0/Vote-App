import React from 'react';
import { render, screen } from '@testing-library/react';
import MetricsTab from '../MetricsTab';
import { SimulationCompareResult } from '../../../types';

vi.mock('../../../hooks/useChartTheme', () => ({
  useChartTheme: () => ({
    isDark: false,
    gridStroke: '#e0e0e0',
    tickFill: '#666',
    tooltipStyle: {},
    refStroke: '#ccc',
  }),
}));

const mockMethods: Record<string, SimulationCompareResult['methods'][string]> = {
  plurality: {
    winner: 'A',
    bayesian_regret: 0.05,
    majority_satisfaction: 0.85,
    strategic_vulnerability: 0.12,
    condorcet_consistent: false,
  },
  irv: {
    winner: 'B',
    bayesian_regret: 0.02,
    majority_satisfaction: 0.92,
    strategic_vulnerability: 0.08,
    condorcet_consistent: true,
  },
};

const mockResult: SimulationCompareResult = {
  condorcet_winner: 'B',
  methods: mockMethods,
};

describe('MetricsTab', () => {
  it('renders card header with title', () => {
    render(
      <MetricsTab
        comparisonResults={[mockResult]}
        allMethodNames={['plurality', 'irv']}
        numSimulations={1}
      />
    );
    expect(screen.getByText(/Comparative metrics/)).toBeInTheDocument();
  });

  it('renders simulation count in header', () => {
    render(
      <MetricsTab
        comparisonResults={[mockResult]}
        allMethodNames={['plurality']}
        numSimulations={5}
      />
    );
    expect(screen.getByText(/5 simulations/)).toBeInTheDocument();
  });

  it('renders metric legend labels', () => {
    render(
      <MetricsTab
        comparisonResults={[mockResult]}
        allMethodNames={['plurality']}
        numSimulations={1}
      />
    );
    expect(screen.getByText(/Bayesian regret/)).toBeInTheDocument();
    expect(screen.getByText(/Majority satisfaction/)).toBeInTheDocument();
    expect(screen.getByText(/Strategic vulnerability/)).toBeInTheDocument();
  });

  it('shows EmptyChart when no comparison results', () => {
    render(
      <MetricsTab
        comparisonResults={[]}
        allMethodNames={[]}
        numSimulations={0}
      />
    );
    expect(screen.getByRole('img')).toBeInTheDocument();
  });

  it('renders chart container when data is present', () => {
    render(
      <MetricsTab
        comparisonResults={[mockResult]}
        allMethodNames={['plurality']}
        numSimulations={1}
      />
    );
    expect(document.querySelector('.recharts-responsive-container')).toBeInTheDocument();
  });
});
