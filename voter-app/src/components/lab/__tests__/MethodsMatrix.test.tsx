import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

let ctx: any;

vi.mock('../../playground/PlaygroundController', () => ({
  usePlaygroundCtx: () => ctx,
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
    ctx = { voters, leaderCandidates: candidates };
    render(<MethodsMatrix />);
    // RULE_LABELS (lib/playgroundVoting.ts) is a fixed, untranslated map used by
    // the static grid — not the i18n'd useVotingLabels() output — so these are
    // French regardless of the active test-run language. Each should appear at
    // least once (live-winners row + grid row).
    expect(screen.getAllByText('Pluralité (1 tour)').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Condorcet (Schulze)').length).toBeGreaterThan(0);
  });

  it('shows a live winner chip per rule when there is an electorate', () => {
    ctx = { voters, leaderCandidates: candidates };
    render(<MethodsMatrix />);
    // At least one of the three candidate names must show up as a live winner.
    const names = ['Alice', 'Bob', 'Carol'];
    const found = names.some((n) => screen.queryAllByText(n).length > 0);
    expect(found).toBe(true);
  });

  it('renders without crashing when there is no electorate yet', () => {
    ctx = { voters: [], leaderCandidates: [] };
    render(<MethodsMatrix />);
    expect(screen.getByText('Méthode')).toBeInTheDocument();
  });

  it('renders the legend for the three satisfaction symbols', () => {
    ctx = { voters, leaderCandidates: candidates };
    render(<MethodsMatrix />);
    // The grid itself uses these symbols in many cells; just confirm each appears.
    expect(screen.getAllByText('✓').length).toBeGreaterThan(0);
    expect(screen.getAllByText('✗').length).toBeGreaterThan(0);
    expect(screen.getAllByText('◐').length).toBeGreaterThan(0);
  });
});
