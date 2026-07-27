import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import GuessPrompt from '../GuessPrompt';
import type { NamedPt } from '../../../lib/playgroundVoting';

const CANDS: NamedPt[] = [
  { name: 'Alice', x: 0, y: 0 },
  { name: 'Bruno', x: 1, y: 0 },
  { name: 'Carla', x: 0, y: 1 },
];

describe('GuessPrompt', () => {
  it('renders a button per candidate and reports the pick', () => {
    const onChange = vi.fn();
    render(<GuessPrompt candidates={CANDS} value={null} onChange={onChange} />);
    expect(screen.getByTestId('play-guess')).toBeInTheDocument();
    CANDS.forEach((_, i) => expect(screen.getByTestId(`play-guess-${i}`)).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('play-guess-1'));
    expect(onChange).toHaveBeenCalledWith(1);
  });

  it('marks the current pick for assistive tech', () => {
    render(<GuessPrompt candidates={CANDS} value={2} onChange={() => {}} />);
    expect(screen.getByTestId('play-guess-2')).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByTestId('play-guess-0')).toHaveAttribute('aria-pressed', 'false');
  });
});
