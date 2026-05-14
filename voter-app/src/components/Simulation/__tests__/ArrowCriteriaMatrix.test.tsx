import React from 'react';
import { render, screen } from '@testing-library/react';
import ArrowCriteriaMatrix from '../ArrowCriteriaMatrix';
import { ArrowCriteriaResult } from '../../../types';

jest.mock('../../shared/MethodTooltip', () => ({ method }: { method: string }) => (
  <span data-testid="method-tooltip">{method}</span>
));
jest.mock('../../shared/ResponsiveTable', () => ({ children }: { children: React.ReactNode }) => (
  <div data-testid="responsive-table">{children}</div>
));

const fullResult: ArrowCriteriaResult = {
  methods: {
    plurality: {
      winner: 'Alice',
      condorcet_winner: false,
      condorcet_loser: true,
      monotonicity: true,
      iia: false,
      iia_violation_rate: 0.15,
      majority: true,
      reversal_symmetry: null,
    },
    irv: {
      winner: 'Bob',
      condorcet_winner: true,
      condorcet_loser: true,
      monotonicity: false,
      iia: false,
      iia_violation_rate: 0.35,
      majority: true,
      reversal_symmetry: true,
    },
  },
  summary: {
    most_criteria_satisfied: 'irv',
    least_criteria_satisfied: 'plurality',
    criteria_satisfaction_count: { plurality: 3, irv: 5 },
  },
};

const emptyResult: ArrowCriteriaResult = {
  methods: {},
  summary: {
    most_criteria_satisfied: '',
    least_criteria_satisfied: '',
    criteria_satisfaction_count: {},
  },
};

describe('ArrowCriteriaMatrix', () => {
  it('renders Arrow impossibility alert', () => {
    render(<ArrowCriteriaMatrix result={fullResult} />);
    expect(screen.getByText(/Arrow's impossibility theorem/)).toBeInTheDocument();
  });

  it('renders method rows from result', () => {
    render(<ArrowCriteriaMatrix result={fullResult} />);
    const tooltips = screen.getAllByTestId('method-tooltip');
    expect(tooltips).toHaveLength(4);
  });

  it('shows best and worst badges', () => {
    render(<ArrowCriteriaMatrix result={fullResult} />);
    expect(screen.getByText('better')).toBeInTheDocument();
    expect(screen.getByText('worse')).toBeInTheDocument();
  });

  it('shows score per method', () => {
    render(<ArrowCriteriaMatrix result={fullResult} />);
    expect(screen.getByText('3 / 6')).toBeInTheDocument();
    expect(screen.getByText('5 / 6')).toBeInTheDocument();
  });

  it('shows empty state when no methods', () => {
    render(<ArrowCriteriaMatrix result={emptyResult} />);
    expect(screen.getByText('No data available.')).toBeInTheDocument();
  });

  it('renders criteria labels', () => {
    render(<ArrowCriteriaMatrix result={fullResult} />);
    expect(screen.getByText('Condorcet winner')).toBeInTheDocument();
    expect(screen.getByText('Monotonicity')).toBeInTheDocument();
    expect(screen.getByText('IIA')).toBeInTheDocument();
  });

  it('renders legend items', () => {
    render(<ArrowCriteriaMatrix result={fullResult} />);
    expect(screen.getByText(/✓ Satisfied/)).toBeInTheDocument();
    expect(screen.getByText(/✗ Violated/)).toBeInTheDocument();
  });
});
