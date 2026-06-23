import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

import DemocracyMap from '../DemocracyMap';
import { LIJPHART_REFERENCE } from '../../../lib/scorecard';

const ENTRIES = [
  { structure: 'pr', label: 'Proportionnelle', index: { mean: 0.82, lo: 0.78, hi: 0.86 } },
  { structure: 'fptp', label: 'Circonscriptions', index: { mean: 0.38, lo: 0.33, hi: 0.44 } },
  { structure: 'mmp', label: 'Mixte', index: { mean: 0.6, lo: 0.55, hi: 0.65 } },
];

describe('DemocracyMap (FA-2)', () => {
  it('plots every reference country and all three live structures', () => {
    render(<DemocracyMap entries={ENTRIES} current="pr" />);
    expect(screen.getByTestId('dm-countries').querySelectorAll('circle').length).toBe(
      LIJPHART_REFERENCE.length
    );
    expect(screen.getByTestId('dm-pr')).toBeInTheDocument();
    expect(screen.getByTestId('dm-fptp')).toBeInTheDocument();
    expect(screen.getByTestId('dm-mmp')).toBeInTheDocument();
  });

  it('positions PR right (consensus) of FPTP (majoritarian) on the strip', () => {
    render(<DemocracyMap entries={ENTRIES} current="fptp" />);
    const markerX = (id: string): number => {
      const d = screen.getByTestId(id).querySelector('path')?.getAttribute('d') ?? '';
      return Number(d.split(' ')[1]); // "M <x> <y> …"
    };
    expect(markerX('dm-pr')).toBeGreaterThan(markerX('dm-fptp'));
  });

  it('highlights the current structure', () => {
    render(<DemocracyMap entries={ENTRIES} current="mmp" />);
    expect(screen.getByTestId('dm-mmp').querySelector('path')?.getAttribute('opacity')).toBe('1');
    expect(screen.getByTestId('dm-pr').querySelector('path')?.getAttribute('opacity')).not.toBe(
      '1'
    );
  });

  it('states the convention (no hidden second dimension)', () => {
    render(<DemocracyMap entries={ENTRIES} current="pr" />);
    expect(screen.getByTestId('democracy-map')).toHaveTextContent('convention déclarée');
    expect(screen.getByTestId('democracy-map')).toHaveTextContent('fédéralisme');
  });
});
