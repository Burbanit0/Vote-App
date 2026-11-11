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
  render(
    <LeaderScene3D voters={sampleVoters(60, 7, 'random', 3)} candidates={CANDS} palette={PALETTE} />
  );
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

  it('rings the elected candidate and moves the ring when the winner changes', () => {
    const voters = sampleVoters(60, 7, 'random', 3);
    const { rerender } = render(
      <LeaderScene3D voters={voters} candidates={CANDS} palette={PALETTE} winner={0} />
    );
    const host = () => screen.getByTestId('scene-winner').parentElement;
    expect(host()).toBe(screen.getByTestId('scene-candidate-0'));
    expect(host()).toHaveTextContent('Winner');
    rerender(<LeaderScene3D voters={voters} candidates={CANDS} palette={PALETTE} winner={2} />);
    expect(host()).toBe(screen.getByTestId('scene-candidate-2'));
    rerender(<LeaderScene3D voters={voters} candidates={CANDS} palette={PALETTE} winner={null} />);
    expect(screen.queryByTestId('scene-winner')).not.toBeInTheDocument();
  });

  it('marks the Condorcet winner, alongside the winner when they coincide', () => {
    const voters = sampleVoters(60, 7, 'random', 3);
    render(
      <LeaderScene3D
        voters={voters}
        candidates={CANDS}
        palette={PALETTE}
        winner={1}
        condorcet={1}
      />
    );
    const group = screen.getByTestId('scene-candidate-1');
    expect(group).toContainElement(screen.getByTestId('scene-condorcet'));
    expect(group).toContainElement(screen.getByTestId('scene-winner'));
    expect(group).toHaveTextContent('Winner · Condorcet');
  });

  it('marks a Condorcet winner the rule did not elect as a ring of its own, without the winner tag', () => {
    render(
      <LeaderScene3D
        voters={sampleVoters(60, 7, 'random', 3)}
        candidates={CANDS}
        palette={PALETTE}
        winner={0}
        condorcet={2}
      />
    );
    const group = screen.getByTestId('scene-candidate-2');
    expect(group).toContainElement(screen.getByTestId('scene-condorcet'));
    expect(group).toHaveTextContent('Condorcet');
    expect(group).not.toHaveTextContent('Winner');
    expect(screen.getByTestId('scene-candidate-0')).toContainElement(
      screen.getByTestId('scene-winner')
    );
  });

  it('follows the electorate and the candidates when they change', () => {
    const near = (name: string): NamedPt =>
      name === 'A' ? { name, x: -0.9, y: 0, z: 0 } : { name, x: 0.9, y: 0, z: 0 };
    const voter = [{ x: -0.8, y: 0, z: 0 }];
    const fill = () => screen.getByTestId('scene-3d').querySelector('circle')!.getAttribute('fill');
    const { rerender } = render(
      <LeaderScene3D voters={voter} candidates={[near('A'), near('B')]} palette={PALETTE} />
    );
    expect(fill()).toBe(PALETTE[0]); // nearest to A
    // The candidates swap sides: the same voter is now nearest to the second one.
    rerender(
      <LeaderScene3D voters={voter} candidates={[near('B'), near('A')]} palette={PALETTE} />
    );
    expect(fill()).toBe(PALETTE[1]);
    // More voters → more dots.
    const before = screen.getByTestId('scene-3d').querySelectorAll('circle').length;
    rerender(
      <LeaderScene3D
        voters={[...voter, { x: 0.5, y: 0.5, z: 0.5 }, { x: 0, y: -0.5, z: 0.2 }]}
        candidates={[near('B'), near('A')]}
        palette={PALETTE}
      />
    );
    expect(screen.getByTestId('scene-3d').querySelectorAll('circle')).toHaveLength(before + 2);
  });
});
