import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

import ParliamentCanvas, { hemicycleSeats } from '../ParliamentCanvas';
import { sampleVoters, type NamedPt } from '../../../lib/playgroundVoting';
import type { AssemblyResult } from '../../../services/assemblyApi';

const PARTIES: NamedPt[] = [
  { name: 'Gauche', x: -0.6, y: -0.2 },
  { name: 'Centre', x: 0.0, y: 0.0 },
  { name: 'Droite', x: 0.6, y: 0.3 },
];

const RESULT: AssemblyResult = {
  structure: 'pr',
  assembly_size: 100,
  majority: 51,
  threshold_waived: false,
  parties: [
    { name: 'Gauche', x: -0.6, y: -0.2, votes: 210, vote_share: 0.35, seats: 35, seat_share: 0.35, district_seats: 0, excluded_by_threshold: false },
    { name: 'Centre', x: 0.0, y: 0.0, votes: 240, vote_share: 0.4, seats: 41, seat_share: 0.41, district_seats: 0, excluded_by_threshold: false },
    { name: 'Droite', x: 0.6, y: 0.3, votes: 150, vote_share: 0.25, seats: 24, seat_share: 0.24, district_seats: 0, excluded_by_threshold: false },
  ],
  gallagher_index: 1.2,
  effective_parties_votes: 2.9,
  effective_parties_seats: 2.8,
  wasted_vote_share: 0.0,
  coalitions: [{ parties: ['Centre', 'Gauche'], seats: 76, span: 0.63 }],
  congruence: {
    electorate_median: [0.02, -0.01],
    assembly_position: [-0.08, 0.0],
    governing_position: [-0.25, -0.08],
    assembly_gap: 0.1,
    governing_gap: 0.28,
  },
  mirror: [
    { region: 'left_lib', electorate_share: 0.3, assembly_share: 0.35 },
    { region: 'left_cons', electorate_share: 0.2, assembly_share: 0.0 },
    { region: 'right_lib', electorate_share: 0.25, assembly_share: 0.41 },
    { region: 'right_cons', electorate_share: 0.25, assembly_share: 0.24 },
  ],
};

function setup(result: AssemblyResult | null = RESULT) {
  const onMoveParty = vi.fn();
  render(
    <ParliamentCanvas
      parties={PARTIES}
      voters={sampleVoters(150, 42, 'random')}
      result={result}
      loading={false}
      onMoveParty={onMoveParty}
    />
  );
  return { onMoveParty };
}

describe('hemicycleSeats', () => {
  it('lays out exactly the requested number of seats', () => {
    const seats = hemicycleSeats(
      100,
      [
        { idx: 0, seats: 35, x: -0.6 },
        { idx: 1, seats: 41, x: 0.0 },
        { idx: 2, seats: 24, x: 0.6 },
      ],
      480,
      250
    );
    expect(seats).toHaveLength(100);
    // Every seat is assigned (counts match the request).
    const byParty = [0, 1, 2].map((i) => seats.filter((s) => s.party === i).length);
    expect(byParty).toEqual([35, 41, 24]);
  });

  it('orders party blocks left → right by ideological x', () => {
    const seats = hemicycleSeats(
      30,
      [
        { idx: 0, seats: 15, x: 0.8 }, // right-most party
        { idx: 1, seats: 15, x: -0.8 }, // left-most party
      ],
      480,
      250
    );
    // The left half of the hemicycle (x < centre) should be mostly party 1.
    const leftSeats = seats.filter((s) => s.x < 240);
    const leftParty1 = leftSeats.filter((s) => s.party === 1).length;
    expect(leftParty1).toBeGreaterThan(leftSeats.length / 2);
  });
});

describe('ParliamentCanvas', () => {
  it('renders territories, voters, hemicycle and metrics', () => {
    setup();
    expect(screen.getByTestId('canvas-parliament')).toBeInTheDocument();
    expect(screen.getByTestId('party-territories').querySelectorAll('path').length).toBe(3);
    expect(screen.getByTestId('hemicycle').querySelectorAll('circle').length).toBe(100);
    expect(screen.getByTestId('assembly-metrics')).toHaveTextContent('1.2');
    expect(screen.getByTestId('votes-seats-bars')).toHaveTextContent('Gauche');
  });

  it('coalition builder sums seats and flags the majority', () => {
    setup();
    fireEvent.click(screen.getByTestId('coalition-toggle-Gauche'));
    expect(screen.getByTestId('coalition-status')).toHaveTextContent('35');
    expect(screen.getByTestId('coalition-status')).toHaveTextContent('pas de majorité');
    fireEvent.click(screen.getByTestId('coalition-toggle-Centre'));
    expect(screen.getByTestId('coalition-status')).toHaveTextContent('76');
    expect(screen.getByTestId('coalition-status')).toHaveTextContent('majorité ✔');
    // Toggle off again.
    fireEvent.click(screen.getByTestId('coalition-toggle-Centre'));
    expect(screen.getByTestId('coalition-status')).toHaveTextContent('pas de majorité');
  });

  it('dragging a party reports its new position', () => {
    const { onMoveParty } = setup();
    fireEvent.mouseDown(screen.getByTestId('party-0'));
    fireEvent.mouseMove(window, { clientX: 120, clientY: 120 });
    expect(onMoveParty).toHaveBeenCalled();
    expect(onMoveParty.mock.calls[0][0]).toBe(0);
  });

  it('renders without a backend result (map only)', () => {
    setup(null);
    expect(screen.getByTestId('canvas-parliament')).toBeInTheDocument();
    expect(screen.queryByTestId('votes-seats-bars')).not.toBeInTheDocument();
    expect(screen.queryByTestId('congruence-overlay')).not.toBeInTheDocument();
  });

  // ── FB-1: representation → governance ─────────────────────────────────────

  it('overlays median/assembly/government markers and reports the gaps', () => {
    setup();
    const overlay = screen.getByTestId('congruence-overlay');
    expect(overlay.querySelector('circle')).toBeTruthy(); // assembly ●
    expect(overlay.querySelector('rect')).toBeTruthy(); // government ◆
    expect(screen.getByTestId('congruence-readout')).toHaveTextContent('0.10');
    expect(screen.getByTestId('congruence-readout')).toHaveTextContent('0.28');
  });

  it('the descriptive mirror shows electorate vs assembly per ideological region', () => {
    setup();
    const mirror = screen.getByTestId('mirror-bars');
    expect(mirror).toHaveTextContent('Gauche · conservateur');
    expect(mirror).toHaveTextContent('20 % → 0 %'); // the unrepresented region
    expect(mirror).toHaveTextContent('25 % → 41 %');
  });
});
