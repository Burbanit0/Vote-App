import React from 'react';
import { render, screen } from '@testing-library/react';
import ScoreVotingComparison from '../ScoreVotingComparison';

jest.mock('../useScoreVotingResults', () => ({
  useScoreVotingResults: () => ({ methodA: { winner: 'Alice' }, methodB: { winner: 'Bob' } }),
}));

jest.mock('../ScoreVotingVisualizations', () => () => <div data-testid="score-viz" />);

describe('ScoreVotingComparison', () => {
  it('renders ScoreVotingVisualizations with results', () => {
    render(<ScoreVotingComparison scores={[]} candidates={['Alice', 'Bob']} />);
    expect(screen.getByTestId('score-viz')).toBeInTheDocument();
  });
});
