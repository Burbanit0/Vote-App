import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import RealElectionAnalysis from '../RealElectionAnalysis';

jest.mock('../../shared/MethodTooltip', () => ({ method }: any) => <span>{method}</span>);

const mockResult = {
  election: {
    key: 'test-2024',
    name: 'Test Election 2024',
    year: 2024,
    country: 'Testland',
    description: 'A test election',
    source: 'Test data',
    candidates: [{ name: 'Alice', party: 'A' }],
    estimated_blank_pct: 0.05,
  },
  plurality_winner: 'Alice',
  first_round_results: { Alice: 600, Bob: 400 },
  methods: {
    plurality: 'Alice',
    irv: 'Alice',
  },
  methods_with_blank: null,
  divergences: [{
    method: 'irv',
    winner: 'Alice',
    winner_with_blank: 'Alice',
    differs_from_plurality: false,
    margin: 0.1,
  }],
  summary: {
    methods_with_different_winner: 0,
    total_methods_with_winner: 2,
  },
  blank_vote_analysis: null,
};

describe('RealElectionAnalysis', () => {
  const onToggle = jest.fn();

  it('renders election name and winner table', () => {
    render(<RealElectionAnalysis result={mockResult as any} blankVoteEnabled={false} blankLoading={false} onToggleBlankVote={onToggle} />);
    expect(screen.getByText('Test Election 2024')).toBeInTheDocument();
    expect(screen.getAllByText('Alice').length).toBeGreaterThanOrEqual(1);
  });

  it('calls onToggleBlankVote when checkbox is clicked', () => {
    render(<RealElectionAnalysis result={mockResult as any} blankVoteEnabled={false} blankLoading={false} onToggleBlankVote={onToggle} />);
    const checkbox = screen.getByRole('checkbox');
    fireEvent.click(checkbox);
    expect(onToggle).toHaveBeenCalledWith(true);
  });
});
