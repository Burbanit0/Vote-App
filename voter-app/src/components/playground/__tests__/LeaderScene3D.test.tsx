import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

import LeaderScene3D from '../LeaderScene3D';
import { sampleVoters, type NamedPt } from '../../../lib/playgroundVoting';

const CANDS: NamedPt[] = [
  { name: 'A', x: -0.5, y: 0, z: -0.4 },
  { name: 'B', x: 0.5, y: 0.2, z: 0.6 },
  { name: 'C', x: 0.0, y: -0.3, z: 0.1 },
];
const PALETTE = ['#2563eb', '#dc2626', '#16a34a'];

function setup() {
  render(<LeaderScene3D voters={sampleVoters(60, 7, 'random', 3)} candidates={CANDS} palette={PALETTE} />);
}

describe('LeaderScene3D', () => {
  it('renders the scene with every candidate and a voter cloud', () => {
    setup();
    expect(screen.getByTestId('scene-3d')).toBeInTheDocument();
    expect(screen.getByTestId('scene-candidate-0')).toBeInTheDocument();
    expect(screen.getByTestId('scene-candidate-2')).toBeInTheDocument();
    // The voter cloud is drawn (many small circles in the scene).
    expect(screen.getByTestId('scene-3d').querySelectorAll('circle').length).toBeGreaterThan(60);
  });

  it('dragging orbits the camera (projected positions change)', () => {
    setup();
    fireEvent.click(screen.getByTestId('scene-spin')); // pause auto-spin first
    const cx = () =>
      screen.getByTestId('scene-candidate-1').querySelector('circle')!.getAttribute('cx');
    const before = cx();
    fireEvent.mouseDown(screen.getByTestId('scene-3d'), { clientX: 100, clientY: 100 });
    fireEvent.mouseMove(window, { clientX: 300, clientY: 200 });
    expect(cx()).not.toBe(before);
  });

  it('the rotation toggle pauses auto-spin', () => {
    setup();
    // Auto-spin is on by default → the button offers to pause.
    expect(screen.getByTestId('scene-spin')).toHaveTextContent('rotation');
    fireEvent.click(screen.getByTestId('scene-spin'));
    expect(screen.getByTestId('scene-spin')).toHaveTextContent('▶');
  });
});
