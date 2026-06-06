import React from 'react';
import { render, screen } from '@testing-library/react';
import CondorcetMatrix from '../CondorcetMatrix';
import { CondorcetMatrixResult } from '../../../types';

const winnerResult: CondorcetMatrixResult = {
  candidates: ['Alice', 'Bob', 'Carol'],
  matrix: {
    Alice: {
      Bob: { pct_a: 0.65, pct_b: 0.35, winner: 'Alice' },
      Carol: { pct_a: 0.72, pct_b: 0.28, winner: 'Alice' },
    },
    Bob: {
      Alice: { pct_a: 0.35, pct_b: 0.65, winner: 'Alice' },
      Carol: { pct_a: 0.55, pct_b: 0.45, winner: 'Bob' },
    },
    Carol: {
      Alice: { pct_a: 0.28, pct_b: 0.72, winner: 'Alice' },
      Bob: { pct_a: 0.45, pct_b: 0.55, winner: 'Bob' },
    },
  },
  condorcet_winner: 'Alice',
  condorcet_cycles: [],
};

const cycleResult: CondorcetMatrixResult = {
  candidates: ['X', 'Y', 'Z'],
  matrix: {
    X: {
      Y: { pct_a: 0.6, pct_b: 0.4, winner: 'X' },
      Z: { pct_a: 0.3, pct_b: 0.7, winner: 'Z' },
    },
    Y: {
      X: { pct_a: 0.4, pct_b: 0.6, winner: 'X' },
      Z: { pct_a: 0.55, pct_b: 0.45, winner: 'Y' },
    },
    Z: {
      X: { pct_a: 0.7, pct_b: 0.3, winner: 'Z' },
      Y: { pct_a: 0.45, pct_b: 0.55, winner: 'Y' },
    },
  },
  condorcet_winner: null,
  condorcet_cycles: [['X', 'Y', 'Z']],
};

const emptyResult: CondorcetMatrixResult = {
  candidates: [],
  matrix: {},
  condorcet_winner: null,
  condorcet_cycles: [],
};

describe('CondorcetMatrix', () => {
  it('renders candidate names in table', () => {
    render(<CondorcetMatrix result={winnerResult} />);
    expect(screen.getAllByText('Alice').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Bob').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Carol').length).toBeGreaterThanOrEqual(1);
  });

  it('displays Condorcet winner when one exists', () => {
    render(<CondorcetMatrix result={winnerResult} />);
    expect(screen.getByText(/Condorcet winner/)).toBeInTheDocument();
  });

  it('shows cycle alert when no Condorcet winner', () => {
    render(<CondorcetMatrix result={cycleResult} />);
    expect(screen.getByText(/No Condorcet winner/)).toBeInTheDocument();
    expect(screen.getByText(/cycle detected/)).toBeInTheDocument();
  });

  it('displays duel percentages', () => {
    render(<CondorcetMatrix result={winnerResult} />);
    expect(screen.getAllByText(/65\.0%/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/72\.0%/).length).toBeGreaterThanOrEqual(1);
  });

  it('shows tie styling for tie duels', () => {
    const tieResult: CondorcetMatrixResult = {
      candidates: ['A', 'B'],
      matrix: {
        A: { B: { pct_a: 0.5, pct_b: 0.5, winner: 'tie' } },
        B: { A: { pct_a: 0.5, pct_b: 0.5, winner: 'tie' } },
      },
      condorcet_winner: null,
      condorcet_cycles: [],
    };
    render(<CondorcetMatrix result={tieResult} />);
    expect(screen.getAllByText(/50\.0%/).length).toBeGreaterThanOrEqual(1);
  });

  it('renders empty state alert when no candidates', () => {
    render(<CondorcetMatrix result={emptyResult} />);
    expect(screen.getByText('No data available.')).toBeInTheDocument();
  });

  it('renders the reading guide', () => {
    render(<CondorcetMatrix result={winnerResult} />);
    expect(screen.getByText('Row candidate wins the duel')).toBeInTheDocument();
    expect(screen.getByText('Row candidate loses')).toBeInTheDocument();
  });
});
