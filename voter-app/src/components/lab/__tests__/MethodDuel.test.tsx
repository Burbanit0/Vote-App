import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

let ctx: unknown;

vi.mock('../../playground/PlaygroundController', () => ({
  useInstrumentCtx: () => ctx,
}));

import MethodDuel from '../MethodDuel';

const candidates = [
  { name: 'Alice', x: -0.6, y: 0 },
  { name: 'Bob', x: 0.6, y: 0 },
  { name: 'Carol', x: 0, y: 0.6 },
];
const voters = Array.from({ length: 30 }, (_, i) => ({
  x: Math.cos((i / 30) * Math.PI * 2) * 0.7,
  y: Math.sin((i / 30) * Math.PI * 2) * 0.7,
}));

describe('MethodDuel', () => {
  it('names a winner per side, except the lottery, which has none', () => {
    ctx = { votingVoters: voters, leaderCandidates: candidates };
    render(<MethodDuel />);
    expect(screen.getByTestId('duel-winner-a')).toHaveTextContent(/Alice|Bob|Carol/);

    fireEvent.change(screen.getByTestId('duel-rule-b'), { target: { value: 'random_ballot' } });
    expect(screen.queryByTestId('duel-winner-b')).not.toBeInTheDocument();
    expect(screen.getByTestId('duel-side-b')).toContainElement(
      screen.getByTestId('no-fixed-winner')
    );
  });
});
