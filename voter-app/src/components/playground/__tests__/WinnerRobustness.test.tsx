import React from 'react';
import { act, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

import WinnerRobustness from '../WinnerRobustness';
import { sampleVoters, type NamedPt, type Pt } from '../../../lib/playgroundVoting';

const CANDS: NamedPt[] = [
  { name: 'A', x: -0.5, y: 0 },
  { name: 'B', x: 0.5, y: 0 },
  { name: 'C', x: 0.0, y: 0.4 },
];
const COLORS = ['#2563eb', '#dc2626', '#16a34a'];

function setup(sampleAtSeed: (seed: number) => Pt[], winner: string | null = 'A') {
  return render(
    <WinnerRobustness
      sampleAtSeed={sampleAtSeed}
      candidates={CANDS}
      rule="plurality"
      baseSeed={42}
      colors={COLORS}
      winner={winner}
    />
  );
}

describe('WinnerRobustness', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('holds the strip’s place, hidden, until the draws land', () => {
    setup((seed) => sampleVoters(60, seed, 'random'));

    // Same shape as the strip (a bar row and one summary line), so the lens switch
    // below it does not move when the draws arrive.
    const pending = screen.getByTestId('winner-robustness-pending');
    expect(pending).toHaveAttribute('aria-hidden', 'true');
    expect(pending).toHaveClass('invisible');
    expect(pending.children).toHaveLength(2);
    expect(pending).toHaveTextContent('A wins in 100% of 140 resamples');
    expect(screen.queryByTestId('winner-robustness')).not.toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(200);
    });
    expect(screen.queryByTestId('winner-robustness-pending')).not.toBeInTheDocument();
    expect(screen.getByTestId('winner-robustness')).toHaveTextContent(
      /wins in \d+% of 140 resamples/
    );
  });

  it('shows nothing once the draws have no winner to report', () => {
    setup(() => [], null);
    expect(screen.getByTestId('winner-robustness-pending')).toHaveTextContent(
      '— wins in 100% of 140 resamples'
    );
    act(() => {
      vi.advanceTimersByTime(200);
    });
    expect(screen.queryByTestId('winner-robustness-pending')).not.toBeInTheDocument();
    expect(screen.queryByTestId('winner-robustness')).not.toBeInTheDocument();
  });
});
