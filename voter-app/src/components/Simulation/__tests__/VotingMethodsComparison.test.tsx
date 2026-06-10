import React from 'react';
import { render, screen } from '@testing-library/react';
import VotingMethodsComparison from '../VotingMethodsComparison';

vi.mock('../VotingMethodVisualizations', () => ({
  __esModule: true,
  default: () => <div data-testid="mock-viz">Visualization</div>,
}));

const mockRankings = [
  { voter_id: 1, ranking: ['Alice', 'Bob', 'Carol'] },
  { voter_id: 2, ranking: ['Bob', 'Alice', 'Carol'] },
  { voter_id: 3, ranking: ['Alice', 'Carol', 'Bob'] },
];

const mockWinners = {
  condorcet_winner: 'Alice',
  plurality_winner: 'Alice',
  borda_winner: 'Bob',
  irv_winner: 'Alice',
};

describe('VotingMethodsComparison', () => {
  it('renders the comparison title', () => {
    render(
      <VotingMethodsComparison
        rankings={mockRankings}
        candidates={['Alice', 'Bob', 'Carol']}
        winners={mockWinners}
      />
    );
    expect(screen.getByText('Voting Method Comparison')).toBeInTheDocument();
  });

  it('renders winners summary grid', () => {
    render(
      <VotingMethodsComparison
        rankings={mockRankings}
        candidates={['Alice', 'Bob', 'Carol']}
        winners={mockWinners}
      />
    );
    expect(screen.getByText('Winners Summary')).toBeInTheDocument();
    expect(screen.getByText('Plurality')).toBeInTheDocument();
    expect(screen.getByText('Borda Count')).toBeInTheDocument();
    expect(screen.getByText('Instant Runoff Voting')).toBeInTheDocument();
  });

  it('displays correct winner names', () => {
    render(
      <VotingMethodsComparison
        rankings={mockRankings}
        candidates={['Alice', 'Bob', 'Carol']}
        winners={mockWinners}
      />
    );
    const aliceWinners = screen.getAllByText('Alice');
    expect(aliceWinners.length).toBeGreaterThanOrEqual(3);
  });

  it('renders VotingMethodVisualizations for each method', () => {
    render(
      <VotingMethodsComparison
        rankings={mockRankings}
        candidates={['Alice', 'Bob', 'Carol']}
        winners={mockWinners}
      />
    );
    const vizElements = screen.getAllByTestId('mock-viz');
    expect(vizElements.length).toBe(12);
  });

  it('skips methods with no winner in summary', () => {
    render(
      <VotingMethodsComparison
        rankings={mockRankings}
        candidates={['Alice', 'Bob', 'Carol']}
        winners={{}}
      />
    );
    // Should not render winner text for methods with no winner
    expect(screen.queryByText(/Winner:/)).not.toBeInTheDocument();
  });

  it('shows method-winner in accordion header when winner exists', () => {
    render(
      <VotingMethodsComparison
        rankings={mockRankings}
        candidates={['Alice', 'Bob', 'Carol']}
        winners={mockWinners}
      />
    );
    expect(screen.getByText(/Plurality.*-.*Winner:.*Alice/)).toBeInTheDocument();
  });
});
