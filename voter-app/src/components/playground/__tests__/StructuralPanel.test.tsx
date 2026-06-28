import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

import type { StructuralFairnessResult } from '../../../services/structuralApi';

const RESULT: StructuralFairnessResult = {
  districts: 20,
  malapportionment: {
    pop_per_seat_ratio: 3.7,
    gallagher_equal: 0.12,
    gallagher_skewed: 0.18,
    min_share_majority_equal: 0.27,
    min_share_majority_skewed: 0.18,
  },
  efficiency_gap: {
    party_a: 'Gauche',
    party_b: 'Droite',
    gap: 0.12,
    wasted_a: 120,
    wasted_b: 60,
  },
  penrose: { equal: 1.9, proportional: 1.9, penrose: 1.0 },
  cumulative: {
    at_large_seats: 5,
    largest_party: 'Gauche',
    seats_bloc: { Gauche: 5, Droite: 0, Marges: 0 },
    seats_cumulative: { Gauche: 3, Droite: 1, Marges: 1 },
    minority_seats_bloc: 0,
    minority_seats_cumulative: 2,
  },
};

const runStructuralFairness = vi.fn();
vi.mock('../../../services/structuralApi', async () => ({
  ...(await vi.importActual('../../../services/structuralApi')),
  runStructuralFairness: (...a: unknown[]) => runStructuralFairness(...a),
}));

import StructuralPanel from '../StructuralPanel';
import { DEFAULT_CONFIG } from '../../../stores/useElectionStore';

beforeEach(() => {
  runStructuralFairness.mockReset().mockResolvedValue(RESULT);
});

function setup() {
  render(<StructuralPanel config={DEFAULT_CONFIG} partyNames={['Gauche', 'Droite', 'Marges']} />);
}

describe('StructuralPanel (FC-2)', () => {
  it('runs with the malapportionment slider value and shows the distortion', async () => {
    setup();
    fireEvent.change(screen.getByTestId('malapportionment-slider'), { target: { value: '0.9' } });
    fireEvent.click(screen.getByTestId('structural-run'));
    await waitFor(() => expect(screen.getByTestId('malapportionment-out')).toBeInTheDocument());
    // trailing args: districts, at-large seats, composed-electorate source (undefined here).
    expect(runStructuralFairness).toHaveBeenCalledWith(DEFAULT_CONFIG, 0.9, 20, 5, undefined);
    // The visible distortion: 18 % of votes can control the seat majority (vs 27 %).
    expect(screen.getByTestId('malapportionment-out')).toHaveTextContent('3.7 : 1');
    expect(screen.getByTestId('malapportionment-out')).toHaveTextContent('18 %');
    expect(screen.getByTestId('malapportionment-out')).toHaveTextContent('27 %');
  });

  it('shows the efficiency gap with its disadvantaged party', async () => {
    setup();
    fireEvent.click(screen.getByTestId('structural-run'));
    await waitFor(() => expect(screen.getByTestId('efficiency-gap-out')).toBeInTheDocument());
    expect(screen.getByTestId('efficiency-gap-out')).toHaveTextContent('12.0 %');
    expect(screen.getByTestId('efficiency-gap-out')).toHaveTextContent('disfavours Gauche');
  });

  it('Penrose equalises citizen power across the three schemes', async () => {
    setup();
    fireEvent.click(screen.getByTestId('structural-run'));
    await waitFor(() => expect(screen.getByTestId('penrose-out')).toBeInTheDocument());
    expect(screen.getByTestId('penrose-out')).toHaveTextContent('√population');
    expect(screen.getByTestId('penrose-out')).toHaveTextContent('1.00');
  });

  it('cumulative voting visibly lifts minority seats vs bloc voting', async () => {
    setup();
    fireEvent.click(screen.getByTestId('structural-run'));
    await waitFor(() => expect(screen.getByTestId('minority-lift')).toBeInTheDocument());
    expect(screen.getByTestId('minority-lift')).toHaveTextContent('0 (bloc)');
    expect(screen.getByTestId('minority-lift')).toHaveTextContent('2');
  });
});
