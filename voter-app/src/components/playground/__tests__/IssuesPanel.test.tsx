import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

import type { IssueVotingResult } from '../../../services/issuesApi';

const PARADOX: IssueVotingResult = {
  mode: 'handcrafted',
  parties: [
    { name: 'A', platform: [1, 1, 1], votes: 3, vote_share: 0.6 },
    { name: 'B', platform: [-1, -1, -1], votes: 2, vote_share: 0.4 },
  ],
  bundled_winner: 'A',
  issues: [
    { label: 'Enjeu 1', yes_share: 0.4, majority: -1, winner_plank: 1, divergent: true },
    { label: 'Enjeu 2', yes_share: 0.4, majority: -1, winner_plank: 1, divergent: true },
    { label: 'Enjeu 3', yes_share: 0.4, majority: -1, winner_plank: 1, divergent: true },
  ],
  divergent_count: 3,
  num_issues: 3,
  ostrogorski_paradox: true,
};

const ALIGNED: IssueVotingResult = {
  ...PARADOX,
  issues: PARADOX.issues.map((i) => ({ ...i, yes_share: 0.7, majority: 1, divergent: false })),
  divergent_count: 0,
  ostrogorski_paradox: false,
};

const runIssueVoting = vi.fn();
const runOstrogorskiDemo = vi.fn();
vi.mock('../../../services/issuesApi', async () => ({
  ...(await vi.importActual('../../../services/issuesApi')),
  runIssueVoting: (...a: unknown[]) => runIssueVoting(...a),
  runOstrogorskiDemo: () => runOstrogorskiDemo(),
}));

import IssuesPanel from '../IssuesPanel';
import { DEFAULT_CONFIG } from '../../../stores/useElectionStore';

beforeEach(() => {
  runIssueVoting.mockReset().mockResolvedValue(ALIGNED);
  runOstrogorskiDemo.mockReset().mockResolvedValue(PARADOX);
});

describe('IssuesPanel (FB-2)', () => {
  it('analyses the shared electorate with the chosen number of issues', async () => {
    render(<IssuesPanel config={DEFAULT_CONFIG} />);
    fireEvent.change(screen.getByTestId('issues-count'), { target: { value: '6' } });
    fireEvent.click(screen.getByTestId('issues-run'));
    await waitFor(() => expect(screen.getByTestId('issues-matrix')).toBeInTheDocument());
    // 3rd arg = the composed-electorate source (undefined here: no playground prop).
    expect(runIssueVoting).toHaveBeenCalledWith(DEFAULT_CONFIG, 6, undefined);
    // Aligned profile: no paradox headline, no divergence marks.
    expect(screen.getByTestId('issues-headline')).not.toHaveTextContent('Paradoxe');
    expect(screen.getByTestId('issues-headline')).toHaveTextContent('0/3');
  });

  it('the constructed demo shows the full Ostrogorski paradox with divergences highlighted', async () => {
    render(<IssuesPanel config={DEFAULT_CONFIG} />);
    fireEvent.click(screen.getByTestId('issues-demo'));
    await waitFor(() =>
      expect(screen.getByTestId('issues-headline')).toHaveTextContent('Paradoxe')
    );
    expect(screen.getByTestId('issues-headline')).toHaveTextContent('3/3');
    // Every issue row carries the divergence mark: majority Non vs platform Oui ✕.
    for (const label of ['Enjeu 1', 'Enjeu 2', 'Enjeu 3']) {
      expect(screen.getByTestId(`issue-row-${label}`)).toHaveTextContent('Non');
      expect(screen.getByTestId(`issue-row-${label}`)).toHaveTextContent('✕');
    }
    // The winner and its platform are listed.
    expect(screen.getByTestId('issues-parties')).toHaveTextContent('A 60 % · OOO');
  });
});
