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
    expect(screen.getByTestId('field-winner')).toHaveTextContent('Winner');
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

  it('offers the new methods in the rule selector', () => {
    setup();
    const select = screen.getByTestId('rule-select') as HTMLSelectElement;
    const values = Array.from(select.options).map((o) => o.value);
    expect(values).toContain('ranked_pairs');
    expect(values).toContain('random_ballot');
  });

  it('defaults to the winner lens: win-region shown, probability overlay absent', () => {
    setup();
    expect(screen.getByTestId('lens-switch')).toBeInTheDocument();
    expect(screen.getByTestId('lens-winner')).toHaveAttribute('aria-checked', 'true');
    expect(screen.queryByTestId('problens')).not.toBeInTheDocument();
    expect(screen.queryByTestId('lottery-bars')).not.toBeInTheDocument();
  });

  it('clicking a lens button calls back', () => {
    const onLensChange = vi.fn();
    setup({ onLensChange });
    fireEvent.click(screen.getByTestId('lens-probability'));
    expect(onLensChange).toHaveBeenCalledWith('probability');
  });

  it('probability lens renders the lottery heatmap + bars and hides the win-region', async () => {
    setup({ lens: 'probability' });
    expect(screen.getByTestId('lens-probability')).toHaveAttribute('aria-checked', 'true');
    expect(screen.queryByTestId('winregion')).not.toBeInTheDocument();
    expect(screen.getByTestId('lottery-bars')).toBeInTheDocument();
    await waitFor(() => {
      const lens = screen.getByTestId('problens');
      expect(lens.querySelectorAll('rect').length).toBe(16 * 16);
    });
  });

  it('manipulation lens tints voters and shows the G-S boundary summary', async () => {
    setup({ lens: 'manipulation' });
    expect(screen.getByTestId('lens-manipulation')).toHaveAttribute('aria-checked', 'true');
    expect(screen.queryByTestId('winregion')).not.toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId('manip-voters')).toBeInTheDocument());
    const summary = screen.getByTestId('manip-summary');
    expect(summary).toBeInTheDocument();
    // The Gibbard-Satterthwaite contrast (random ballot at 0%) is stated inline.
    expect(summary).toHaveTextContent('0 %');
    expect(summary).toHaveTextContent(/Gibbard/);
  });

  it('criteria lens renders the matrix and rings the Condorcet winner on the map', async () => {
    // A centrist Condorcet winner exists with this layout.
    setup({
      lens: 'criteria',
      candidates: [
        { name: 'L', x: -0.8, y: 0 },
        { name: 'M', x: 0, y: 0 },
        { name: 'R', x: 0.8, y: 0 },
      ],
      voters: [
        ...Array.from({ length: 40 }, () => ({ x: -0.7, y: 0 })),
        ...Array.from({ length: 25 }, () => ({ x: 0, y: 0 })),
        ...Array.from({ length: 40 }, () => ({ x: 0.7, y: 0 })),
      ],
    });
    expect(screen.getByTestId('lens-criteria')).toHaveAttribute('aria-checked', 'true');
    expect(screen.queryByTestId('winregion')).not.toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId('criteria-matrix')).toBeInTheDocument());
    // One row per rule (24 leader rules) and a Condorcet ring on the map.
    expect(screen.getByTestId('criteria-matrix').querySelectorAll('tbody tr').length).toBe(24);
    expect(screen.getByTestId('condorcet-marker')).toBeInTheDocument();
    // The constructed no-show paradox demo accompanies the criteria matrix.
    expect(screen.getByTestId('noshow-demo')).toBeInTheDocument();
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
    const { onMoveCandidate } = setup({
      dims: 3,
      candidates: cands,
      voters: sampleVoters(80, 1, 'random', 3),
    });
    expect(screen.getByTestId('z-controls')).toBeInTheDocument();
    fireEvent.change(screen.getByTestId('z-slider-2'), { target: { value: '0.6' } });
    expect(onMoveCandidate).toHaveBeenCalledWith(2, cands[2].x, cands[2].y, 0.6);
  });
});
