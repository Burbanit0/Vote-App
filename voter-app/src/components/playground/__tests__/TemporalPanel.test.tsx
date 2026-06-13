import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

import type { TemporalResult } from '../../../services/assemblyApi';

// Two-round fixture with parties drifting and the lead changing.
function mkResult(winnerLast = 'B'): TemporalResult {
  return {
    rounds: [
      {
        round: 0,
        parties: [
          { name: 'A', x: -0.5, y: 0, vote_share: 0.55, seats: 55 },
          { name: 'B', x: 0.5, y: 0, vote_share: 0.45, seats: 45 },
        ],
        winner: 'A',
        enp_votes: 2.0,
        enp_seats: 1.98,
        gallagher: 0.01,
        polarization: 0.5,
        alternation: false,
        congruence_gap: 0.12,
      },
      {
        round: 1,
        parties: [
          { name: 'A', x: -0.4, y: 0.05, vote_share: 0.48, seats: 48 },
          { name: 'B', x: 0.4, y: -0.05, vote_share: 0.52, seats: 52 },
        ],
        winner: winnerLast,
        enp_votes: 1.9,
        enp_seats: 1.92,
        gallagher: 0.01,
        polarization: 0.42,
        alternation: true,
        congruence_gap: 0.08,
      },
    ],
    alternation_rate: 1,
    enp_votes_initial: 2.0,
    enp_votes_final: 1.9,
    polarization_initial: 0.5,
    polarization_final: 0.42,
  };
}

const runTemporal = vi.fn();
vi.mock('../../../services/assemblyApi', async () => ({
  ...(await vi.importActual('../../../services/assemblyApi')),
  runTemporal: (...args: unknown[]) => runTemporal(...args),
}));

import TemporalPanel from '../TemporalPanel';
import { DEFAULT_CONFIG, DEFAULT_PLAYGROUND } from '../../../stores/useElectionStore';

beforeEach(() => {
  runTemporal.mockReset();
  runTemporal.mockResolvedValue(mkResult());
});

function setup() {
  render(<TemporalPanel config={DEFAULT_CONFIG} playground={DEFAULT_PLAYGROUND} />);
}

describe('TemporalPanel (FA-3)', () => {
  it('runs N cycles on demand and renders trails, lines and readouts', async () => {
    setup();
    expect(screen.queryByTestId('temporal-trails')).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId('temporal-run'));
    await waitFor(() => expect(screen.getByTestId('temporal-trails')).toBeInTheDocument());
    // One trail per party.
    expect(screen.getByTestId('trail-0')).toBeInTheDocument();
    expect(screen.getByTestId('trail-1')).toBeInTheDocument();
    expect(screen.getByTestId('enp-line')).toBeInTheDocument();
    expect(screen.getByTestId('polarization-line')).toBeInTheDocument();
    expect(screen.getByTestId('temporal-readouts')).toHaveTextContent('100 %'); // alternance
    expect(screen.getByTestId('temporal-readouts')).toHaveTextContent('2.0 → 1.9');
  });

  it('the scrubber moves through rounds (winner readout follows)', async () => {
    setup();
    fireEvent.click(screen.getByTestId('temporal-run'));
    await waitFor(() => expect(screen.getByTestId('temporal-scrub')).toBeInTheDocument());
    // Lands on the final round by default.
    expect(screen.getByTestId('temporal-round-winner')).toHaveTextContent('B');
    fireEvent.change(screen.getByTestId('temporal-scrub'), { target: { value: '0' } });
    expect(screen.getByTestId('temporal-round-winner')).toHaveTextContent('A');
  });

  it('comparing a second structure runs it from the same start (dashed line)', async () => {
    setup();
    fireEvent.change(screen.getByTestId('temporal-compare'), { target: { value: 'fptp' } });
    fireEvent.click(screen.getByTestId('temporal-run'));
    await waitFor(() => expect(screen.getByTestId('enp-line-compare')).toBeInTheDocument());
    expect(runTemporal).toHaveBeenCalledTimes(2);
    // Second call carries the comparison structure.
    expect(runTemporal.mock.calls[1][2]).toBe('fptp');
  });
});
