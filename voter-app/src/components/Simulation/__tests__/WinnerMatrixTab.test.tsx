import React from 'react';
import { render, screen } from '@testing-library/react';
import WinnerMatrixTab from '../WinnerMatrixTab';

vi.mock('../../shared/MethodTooltip', () => ({
  default: ({ method }: any) => <span>{method}</span>,
}));
vi.mock('../../shared/ResponsiveTable', () => ({
  default: ({ children, className }: any) => <div className={className}>{children}</div>,
}));

const mockResults = [
  {
    methods: {
      plurality: {
        winner: 'Alice',
        condorcet_consistent: true,
        bayesian_regret: 0.1,
        majority_satisfaction: 0.8,
        strategic_vulnerability: 0.2,
      },
    },
    condorcet_winner: 'Alice',
  },
  {
    methods: {
      plurality: {
        winner: 'Alice',
        condorcet_consistent: true,
        bayesian_regret: 0.15,
        majority_satisfaction: 0.7,
        strategic_vulnerability: 0.25,
      },
    },
    condorcet_winner: 'Alice',
  },
];

const baseProps = {
  comparisonResults: mockResults,
  resultsB: null,
  allMethodNames: ['plurality'],
  candidateColorMap: { Alice: '#4e79a7' },
  configA: { numVoters: 500, candidateInput: 'Alice, Bob', ideology_distribution: 'random' },
  configB: {
    numVoters: 500,
    candidateInput: 'Alice, Bob, Charlie',
    ideology_distribution: 'random',
  },
  numSimulations: 2,
  scenarioCount: 1 as const,
};

describe('WinnerMatrixTab', () => {
  it('renders winner matrix table', () => {
    render(<WinnerMatrixTab {...baseProps} />);
    expect(screen.getAllByText('plurality').length).toBeGreaterThanOrEqual(1);
  });

  it('renders scenario comparison when scenarioCount is 2', () => {
    const props = { ...baseProps, scenarioCount: 2 as const, resultsB: [...mockResults] };
    render(<WinnerMatrixTab {...props} />);
    expect(screen.getByText(/Scenario A/)).toBeInTheDocument();
    expect(screen.getByText(/Scenario B/)).toBeInTheDocument();
    expect(screen.getByText(/Differences/)).toBeInTheDocument();
  });

  it('renders color legend', () => {
    render(<WinnerMatrixTab {...baseProps} />);
    expect(screen.getAllByText('Alice').length).toBeGreaterThanOrEqual(1);
  });
});
