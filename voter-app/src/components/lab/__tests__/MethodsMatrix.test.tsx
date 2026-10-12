import React from 'react';
import { render, screen, fireEvent, within } from '@testing-library/react';
import '@testing-library/jest-dom';

let ctx: any;

vi.mock('../../playground/PlaygroundController', () => ({
  useInstrumentCtx: () => ctx,
}));

import MethodsMatrix from '../MethodsMatrix';

const candidates = [
  { name: 'Alice', x: -0.6, y: 0 },
  { name: 'Bob', x: 0.6, y: 0 },
  { name: 'Carol', x: 0, y: 0.6 },
];

// A small but real electorate — ruleWinner() runs the actual voting math, no mock.
const voters = Array.from({ length: 30 }, (_, i) => ({
  x: Math.cos((i / 30) * Math.PI * 2) * 0.7,
  y: Math.sin((i / 30) * Math.PI * 2) * 0.7,
}));

describe('MethodsMatrix', () => {
  it('renders the static criteria grid with a row per compared method', () => {
    ctx = { expressedVoters: voters, leaderCandidates: candidates };
    render(<MethodsMatrix />);
    // Rule names come from useVotingLabels(), so they follow the language (tests run
    // in English). Each should appear at least once (live-winners row + grid row).
    expect(screen.getAllByText('Plurality (1 round)').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Condorcet (Schulze)').length).toBeGreaterThan(0);
  });

  it('shows a live winner chip per rule when there is an electorate', () => {
    ctx = { expressedVoters: voters, leaderCandidates: candidates };
    render(<MethodsMatrix />);
    // At least one of the three candidate names must show up as a live winner.
    const names = ['Alice', 'Bob', 'Carol'];
    const found = names.some((n) => screen.queryAllByText(n).length > 0);
    expect(found).toBe(true);
    // …except the lottery, which has no fixed winner.
    expect(screen.getAllByTestId('no-fixed-winner')).toHaveLength(1);
  });

  it('renders without crashing when there is no electorate yet', () => {
    ctx = { expressedVoters: [], leaderCandidates: [] };
    render(<MethodsMatrix />);
    expect(screen.getByText('Method')).toBeInTheDocument();
  });

  it('renders the legend for the three satisfaction symbols', () => {
    ctx = { expressedVoters: voters, leaderCandidates: candidates };
    render(<MethodsMatrix />);
    // The grid itself uses these symbols in many cells; just confirm each appears.
    expect(screen.getAllByText('✓').length).toBeGreaterThan(0);
    expect(screen.getAllByText('✗').length).toBeGreaterThan(0);
    expect(screen.getAllByText('◐').length).toBeGreaterThan(0);
  });

  // W1.4: every cell says what its verdict rests on (method_criteria.json's basis and
  // source), with a report link that names the cell.
  describe('what a cell rests on', () => {
    const pick = (cell: string) => {
      fireEvent.click(screen.getByTestId(`matrix-cell-${cell}`));
      return screen.getByTestId('matrix-cell-source');
    };

    it('a literature cell names its source and its note, and reports itself', () => {
      ctx = { expressedVoters: voters, leaderCandidates: candidates };
      render(<MethodsMatrix />);
      const panel = pick('plurality-strategy_proof');
      expect(panel).toHaveTextContent('From the literature');
      expect(panel).toHaveTextContent('Gibbard (1973)');
      expect(panel).toHaveTextContent('Gibbard-Satterthwaite');
      expect(within(panel).getByTestId('report-content-error')).toHaveAttribute(
        'href',
        expect.stringContaining(`where=${encodeURIComponent('matrix:plurality/strategy_proof')}`)
      );
      expect(screen.getByTestId('matrix-cell-plurality-strategy_proof')).toHaveAttribute(
        'title',
        expect.stringContaining('Gibbard (1973)')
      );
    });

    it('an unsourced literature cell says its source is still to be confirmed', () => {
      ctx = { expressedVoters: voters, leaderCandidates: candidates };
      render(<MethodsMatrix />);
      expect(pick('plurality-iia')).toHaveTextContent('to be confirmed');
      // Hover and assistive tech get the same text as the open row.
      expect(screen.getByTestId('matrix-cell-plurality-iia')).toHaveAccessibleName(
        expect.stringContaining('to be confirmed')
      );
      expect(screen.getByTestId('matrix-cell-plurality-iia')).toHaveAttribute(
        'aria-expanded',
        'true'
      );
    });

    it('an engine-tested cell and a variant say so', () => {
      ctx = { expressedVoters: voters, leaderCandidates: candidates };
      render(<MethodsMatrix />);
      const tested = pick('plurality-condorcet_winner');
      expect(tested).toHaveTextContent('Tested on both engines');
      expect(tested).not.toHaveTextContent('Source');
      const variant = pick('irv-condorcet_loser');
      expect(variant).toHaveTextContent('departs from the textbook verdict');
      expect(variant).toHaveTextContent('eliminates tied last places together');
    });

    it('a second click on the picked cell closes it', () => {
      ctx = { expressedVoters: voters, leaderCandidates: candidates };
      render(<MethodsMatrix />);
      pick('plurality-iia');
      fireEvent.click(screen.getByTestId('matrix-cell-plurality-iia'));
      expect(screen.queryByTestId('matrix-cell-source')).not.toBeInTheDocument();
    });
  });
});
