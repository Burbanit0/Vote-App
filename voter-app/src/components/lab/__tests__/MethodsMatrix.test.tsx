import React from 'react';
import { render, screen } from '@testing-library/react';
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
    ctx = { voters, leaderCandidates: candidates };
    render(<MethodsMatrix />);
    // Rule names come from useVotingLabels(), so they follow the language (tests run
    // in English). Each should appear at least once (live-winners row + grid row).
    expect(screen.getAllByText('Plurality (1 round)').length).toBeGreaterThan(0);
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
    expect(screen.getByText('Method')).toBeInTheDocument();
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
