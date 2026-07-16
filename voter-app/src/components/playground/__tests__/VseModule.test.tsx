import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

import VseModule from '../VseModule';
import { VSE_RULES } from '../../../lib/playgroundBehavior';
import { sampleVoters, type NamedPt } from '../../../lib/playgroundVoting';

// The centre squeeze on a bimodal electorate — the field where strategy actually bites.
const SQUEEZE: NamedPt[] = [
  { name: 'Gauche', x: -0.55, y: 0 },
  { name: 'Centre', x: 0, y: 0 },
  { name: 'Droite', x: 0.55, y: 0 },
];
const squeezeSampler = (seed: number) => sampleVoters(300, seed, 'polarized', 1);
// A consensual Gaussian electorate: every method already elects the best candidate.
const consensualSampler = (seed: number) => sampleVoters(300, seed, 'random', 1);

describe('VseModule', () => {
  it('draws one curve per method plus a legend', () => {
    render(<VseModule sampleAtSeed={squeezeSampler} baseSeed={42} candidates={SQUEEZE} />);
    expect(screen.getByTestId('vse-chart')).toBeInTheDocument();
    for (const rule of VSE_RULES) {
      expect(screen.getByTestId(`vse-line-${rule}`)).toBeInTheDocument();
      expect(screen.getByTestId(`vse-legend-${rule}`)).toBeInTheDocument();
    }
  });

  it('hovering a method isolates its curve', () => {
    render(<VseModule sampleAtSeed={squeezeSampler} baseSeed={42} candidates={SQUEEZE} />);
    const other = screen.getByTestId('vse-line-borda');
    expect(other).toHaveAttribute('opacity', '1');
    fireEvent.mouseEnter(screen.getByTestId('vse-legend-plurality'));
    expect(screen.getByTestId('vse-line-plurality')).toHaveAttribute('stroke-width', '3');
    expect(other).toHaveAttribute('opacity', '0.25');
  });

  it('states the convention rather than smuggling the strategic model', () => {
    render(<VseModule sampleAtSeed={squeezeSampler} baseSeed={42} candidates={SQUEEZE} />);
    expect(screen.getByTestId('vse-module')).toHaveTextContent('Duverger compression');
    expect(screen.getByTestId('vse-module')).toHaveTextContent('lie on the ballot');
  });

  it('calls a flat chart what it is instead of leaving seven identical lines', () => {
    render(<VseModule sampleAtSeed={consensualSampler} baseSeed={42} candidates={SQUEEZE} />);
    expect(screen.getByTestId('vse-flat')).toHaveTextContent(
      'every method already elects the same candidate'
    );
  });

  it('needs at least two candidates', () => {
    render(<VseModule sampleAtSeed={squeezeSampler} baseSeed={42} candidates={[SQUEEZE[0]]} />);
    expect(screen.queryByTestId('vse-chart')).not.toBeInTheDocument();
    expect(screen.getByText(/at least two candidates/i)).toBeInTheDocument();
  });
});
