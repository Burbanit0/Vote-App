import React from 'react';
import { render, screen } from '@testing-library/react';
import { Spinner } from '../spinner';
import { TallyGate, TallyLoader, gatesOf } from '../tally';

const strokeIndices = (root: Element) =>
  [...root.querySelectorAll('line.tally-loop-stroke')].map((l) =>
    Number((l as SVGLineElement).style.getPropertyValue('--i'))
  );

describe('tally', () => {
  it('counts in gates of five', () => {
    expect(gatesOf(0)).toEqual([]);
    expect(gatesOf(5)).toEqual([5]);
    expect(gatesOf(12)).toEqual([5, 5, 2]);
  });

  it('draws four uprights, then the strike as the fifth stroke', () => {
    const { container, rerender } = render(<TallyGate k={4} />);
    expect(container.querySelectorAll('line')).toHaveLength(4);
    rerender(<TallyGate k={5} />);
    const lines = container.querySelectorAll('line');
    expect(lines).toHaveLength(5);
    // The strike crosses the gate: it runs from the bottom-left to the top-right.
    expect(lines[4]).toHaveAttribute('x1', '0.5');
    expect(lines[4]).toHaveAttribute('x2', '21');
    expect(container.querySelector('svg')).toHaveAttribute('aria-hidden', 'true');
  });

  it('the spinner is one gate counted in a loop, announced as loading', () => {
    render(<Spinner size="sm" className="me-2" />);
    const spinner = screen.getByRole('status', { name: 'loading' });
    expect(spinner).not.toHaveAttribute('aria-hidden');
    expect(spinner).toHaveClass('tally-loop', 'me-2');
    expect(spinner.style.getPropertyValue('--tally-n')).toBe('5');
    expect(strokeIndices(spinner)).toEqual([0, 1, 2, 3, 4]);
  });

  it('the loader counts its gates in one sequence, beside its label', () => {
    render(<TallyLoader data-testid="wait" label="Counting…" />);
    const loader = screen.getByTestId('wait');
    expect(loader).toHaveAttribute('role', 'status');
    expect(loader).toHaveTextContent('Counting…');
    const row = loader.querySelector('.tally-loop') as HTMLElement;
    expect(row.style.getPropertyValue('--tally-n')).toBe('15');
    // Three gates, their strokes numbered on from one gate to the next.
    expect(row.querySelectorAll('svg')).toHaveLength(3);
    expect(strokeIndices(row)).toEqual([...Array(15).keys()]);
  });

  it('passes the wrapper attributes through', () => {
    render(<TallyLoader label="…" id="wait" aria-busy="true" />);
    expect(screen.getByRole('status')).toHaveAttribute('id', 'wait');
    expect(screen.getByRole('status')).toHaveAttribute('aria-busy', 'true');
  });
});
