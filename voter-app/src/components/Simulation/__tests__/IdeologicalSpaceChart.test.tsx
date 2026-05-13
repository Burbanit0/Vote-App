import React from 'react';
import { render, screen } from '@testing-library/react';
import IdeologicalSpaceChart from '../IdeologicalSpaceChart';

jest.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  ScatterChart: ({ children }: any) => <div>{children}</div>,
  Scatter: () => <div />,
  CartesianGrid: () => <div />,
  ReferenceLine: () => <div />,
  Tooltip: () => <div />,
  XAxis: () => <div />,
  YAxis: () => <div />,
  ZAxis: () => <div />,
}));

const mockVoters = [
  { id: 1, political_lean_normalized: -0.5, voting_style: 'strategic', issue_positions: {} },
  { id: 2, political_lean_normalized: 0.3, voting_style: 'honest', issue_positions: {} },
];

const mockCandidates = [
  { id: 1, name: 'Alice', party: 'A', ideology_position: -0.4, policies: {} },
  { id: 2, name: 'Bob', party: 'B', ideology_position: 0.5, policies: {} },
];

describe('IdeologicalSpaceChart', () => {
  it('renders chart title', () => {
    render(<IdeologicalSpaceChart voters={mockVoters} candidates={mockCandidates} />);
    expect(screen.getByText('Espace idéologique 2D')).toBeInTheDocument();
  });

  it('renders method buttons when winnersByMethod provided', () => {
    const winners = { plurality: 'Alice' };
    render(<IdeologicalSpaceChart voters={mockVoters} candidates={mockCandidates} winnersByMethod={winners} />);
    expect(screen.getAllByText('Plurality').length).toBeGreaterThanOrEqual(1);
  });
});
