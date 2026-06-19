import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

import NoShowParadox, { noShowWinner } from '../NoShowParadox';

describe('NoShowParadox', () => {
  it('elects B when everyone votes, A once C-supporters abstain (no-show paradox)', () => {
    // Full turnout → B wins the runoff; C-supporters (C>A>B) get their last choice.
    expect(noShowWinner(0)).toBe(1); // B
    // With 3 C-supporters abstaining, A enters the runoff and wins — A is their 2nd choice.
    expect(noShowWinner(3)).toBe(0); // A
    // The flip is robust beyond the tie point.
    expect(noShowWinner(2)).toBe(0);
  });

  it('renders the verdict and flips it via the abstention slider', () => {
    render(<NoShowParadox />);
    expect(screen.getByTestId('noshow-demo')).toBeInTheDocument();
    // At rest (nobody abstains) there is no paradox highlighted.
    expect(screen.getByTestId('noshow-verdict')).not.toHaveTextContent(/Paradoxe/);
    // Move the slider to make C-supporters abstain → the paradox appears.
    fireEvent.change(screen.getByTestId('noshow-abstain'), { target: { value: '3' } });
    expect(screen.getByTestId('noshow-verdict')).toHaveTextContent(/Paradoxe/);
  });
});
