import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

import LeaderCanvas from '../LeaderCanvas';
import { sampleVoters, type NamedPt } from '../../../lib/playgroundVoting';

const CANDS: NamedPt[] = [
  { name: 'A', x: -0.5, y: 0 },
  { name: 'B', x: 0.5, y: 0 },
  { name: 'C', x: 0.0, y: 0.4 },
];

function setup(overrides: Partial<React.ComponentProps<typeof LeaderCanvas>> = {}) {
  const onRuleChange = vi.fn();
  const onMoveCandidate = vi.fn();
  render(
    <LeaderCanvas
      candidates={CANDS}
      voters={sampleVoters(120, 42, 'random')}
      rule="plurality"
      dims={2}
      onRuleChange={onRuleChange}
      onMoveCandidate={onMoveCandidate}
      {...overrides}
    />
  );
  return { onRuleChange, onMoveCandidate };
}

describe('LeaderCanvas', () => {
  it('renders the plane, candidates, and the field winner', () => {
    setup();
    expect(screen.getByTestId('leader-canvas')).toBeInTheDocument();
    expect(screen.getByTestId('candidate-0')).toBeInTheDocument();
    expect(screen.getByTestId('candidate-2')).toBeInTheDocument();
    expect(screen.getByTestId('median-marker')).toBeInTheDocument();
    expect(screen.getByTestId('field-winner')).toHaveTextContent('Vainqueur');
  });

  it('computes the win/entry-region overlay (debounced) with one cell per grid square', async () => {
    setup();
    await waitFor(() => {
      const region = screen.getByTestId('winregion');
      expect(region.querySelectorAll('rect').length).toBe(16 * 16);
    });
  });

  it('changing the rule selector calls back', () => {
    const { onRuleChange } = setup();
    fireEvent.change(screen.getByTestId('rule-select'), { target: { value: 'irv' } });
    expect(onRuleChange).toHaveBeenCalledWith('irv');
  });

  it('grabbing a candidate then dragging moves it', () => {
    const { onMoveCandidate } = setup();
    // Grab candidate 0, then a window mousemove should report its new domain position.
    fireEvent.mouseDown(screen.getByTestId('candidate-0'));
    fireEvent.mouseMove(window, { clientX: 100, clientY: 100 });
    expect(onMoveCandidate).toHaveBeenCalled();
    expect(onMoveCandidate.mock.calls[0][0]).toBe(0);
  });

  it('1-D collapses to a line: dragging forces y=0 and no z controls', () => {
    const { onMoveCandidate } = setup({ dims: 1, voters: sampleVoters(80, 1, 'random', 1) });
    expect(screen.getByTestId('leader-canvas')).toHaveAttribute('data-dims', '1');
    expect(screen.queryByTestId('z-controls')).not.toBeInTheDocument();
    fireEvent.mouseDown(screen.getByTestId('candidate-0'));
    fireEvent.mouseMove(window, { clientX: 200, clientY: 300 });
    // y is pinned to 0 regardless of the pointer's vertical position.
    expect(onMoveCandidate.mock.calls[0][1]).toBeTypeOf('number');
    expect(onMoveCandidate.mock.calls[0][2]).toBe(0);
  });

  it('3-D exposes per-candidate z sliders that report the new z', () => {
    const cands: NamedPt[] = CANDS.map((c) => ({ ...c, z: 0 }));
    const { onMoveCandidate } = setup({ dims: 3, candidates: cands, voters: sampleVoters(80, 1, 'random', 3) });
    expect(screen.getByTestId('z-controls')).toBeInTheDocument();
    fireEvent.change(screen.getByTestId('z-slider-2'), { target: { value: '0.6' } });
    expect(onMoveCandidate).toHaveBeenCalledWith(2, cands[2].x, cands[2].y, 0.6);
  });
});
