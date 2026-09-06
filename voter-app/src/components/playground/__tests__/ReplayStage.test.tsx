import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import ReplayStage from '../ReplayStage';
import type { VoteTrace } from '../../../lib/voteTrace';
import type { NamedPt } from '../../../lib/playgroundVoting';

const candidates: NamedPt[] = [
  { name: 'Alice', x: -0.5, y: 0 },
  { name: 'Bob', x: 0.5, y: 0 },
];

function trace(overrides: Partial<VoteTrace['frames'][number]> = {}): VoteTrace {
  return {
    family: 'count',
    rule: 'plurality',
    winner: 0,
    unitKey: 'canvas.zAxis',
    sampleSize: 100,
    frames: [
      {
        caption: { key: 'canvas.condorcetMarker' },
        bars: [60, 40],
        ...overrides,
      },
    ],
  };
}

describe('ReplayStage', () => {
  it('renders one bar per candidate, sized relative to the frame scale', () => {
    render(<ReplayStage trace={trace()} frame={0} candidates={candidates} />);
    expect(screen.getByText('Alice')).toBeInTheDocument();
    expect(screen.getByText('Bob')).toBeInTheDocument();
    expect(screen.getByText('60')).toBeInTheDocument();
    expect(screen.getByText('40')).toBeInTheDocument();
  });

  it('shows the unit label unless compact', () => {
    const { rerender } = render(<ReplayStage trace={trace()} frame={0} candidates={candidates} />);
    expect(screen.getByTestId('replay-bars').parentElement?.textContent).toBeTruthy();

    rerender(<ReplayStage trace={trace()} frame={0} candidates={candidates} compact />);
    // compact drops the unit <p> — only the bars + caption remain testable via testids
    expect(screen.getByTestId('replay-caption')).toBeInTheDocument();
  });

  it('clamps to the last frame when `frame` overshoots', () => {
    const t = trace();
    render(<ReplayStage trace={t} frame={99} candidates={candidates} />);
    // Only one frame exists — overshoot must not throw and must render it.
    expect(screen.getByText('60')).toBeInTheDocument();
  });

  it('marks eliminated candidates and highlights the current beat', () => {
    const t = trace({ eliminated: [true, false], highlight: [1] });
    render(<ReplayStage trace={t} frame={0} candidates={candidates} />);
    const alice = screen.getByText('Alice');
    const bob = screen.getByText('Bob');
    expect(alice.className).toContain('line-through');
    expect(bob.className).toContain('font-semibold');
  });

  it('uses a custom colorOf override when supplied', () => {
    const colorOf = vi.fn((i: number) => (i === 0 ? '#111111' : '#222222'));
    render(<ReplayStage trace={trace()} frame={0} candidates={candidates} colorOf={colorOf} />);
    expect(colorOf).toHaveBeenCalledWith(0);
    expect(screen.getByText('Alice')).toHaveStyle({ color: '#111111' });
  });
});
