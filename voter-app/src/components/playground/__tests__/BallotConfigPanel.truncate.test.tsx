import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

vi.mock('../../../services/profileApi', () => ({
  runProfileSimulate: vi.fn().mockRejectedValue(new Error('not under test')),
}));
vi.mock('../../../services/assemblyApi', () => ({
  runAssembly: vi.fn().mockRejectedValue(new Error('not under test')),
  runAssemblyScorecard: vi.fn().mockRejectedValue(new Error('not under test')),
}));

import { PlaygroundProvider } from '../PlaygroundController';
import BallotConfigPanel from '../BallotConfigPanel';
import {
  useElectionStore,
  DEFAULT_CONFIG,
  DEFAULT_PLAYGROUND,
} from '../../../stores/useElectionStore';

// A truncated ballot ranks the first n candidates, and the engine caps n at the candidate count.
// The stored value can sit above the count (a preset with two candidates, or the candidate editor
// removing down to two): the slider and its label must show what the engine will use.

function mountWith(candidateCount: number, truncate_at: number) {
  useElectionStore.setState({
    config: { ...DEFAULT_CONFIG, candidates: DEFAULT_CONFIG.candidates.slice(0, candidateCount) },
    playground: {
      ...DEFAULT_PLAYGROUND,
      ballot: { ...DEFAULT_PLAYGROUND.ballot, type: 'rank_truncated', truncate_at },
    },
  });
  render(
    <PlaygroundProvider>
      <BallotConfigPanel />
    </PlaygroundProvider>
  );
}

beforeEach(() => localStorage.clear());

describe('BallotConfigPanel: the truncation slider', () => {
  it('shows the stored value when the field is large enough', () => {
    mountWith(3, 3);
    expect(screen.getByTestId('ballot-truncate')).toHaveValue('3');
    expect(screen.getByText(/3/, { selector: 'label' })).toBeInTheDocument();
  });

  it('shows the cap, not a stored value above the candidate count', () => {
    mountWith(2, 3);
    const slider = screen.getByTestId('ballot-truncate');
    expect(slider).toHaveValue('2');
    expect(slider).toHaveAttribute('max', '2');
    expect(screen.getByText(/2/, { selector: 'label' })).toBeInTheDocument();
    expect(screen.queryByText(/3/, { selector: 'label' })).not.toBeInTheDocument();
  });
});
