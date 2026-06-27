import { describe, it, expect } from 'vitest';
import { equilibriumReport } from './playgroundEquilibrium';
import type { NamedPt, Pt } from './playgroundVoting';

// A 1-D vote-utile scenario, the classic Duverger squeeze:
//   A (left)  B (centre)  C (right)
// Left bloc 40 ranks A>B>C, centre bloc 25 ranks B>A>C, right bloc 35 ranks C>B>A.
// Sincere plurality elects A (40 > 35 > 25), but the centrist B is the Condorcet
// winner (beats A 60-40, beats C 65-35). Right voters, whose worst case is A,
// compromise onto B → plurality settles on B. A Condorcet method already elects B
// and nothing can dislodge it, so it stays put.
function bloc(x: number, n: number): Pt[] {
  return Array.from({ length: n }, () => ({ x, y: 0 }));
}
const VOTERS: Pt[] = [...bloc(-0.8, 40), ...bloc(-0.1, 25), ...bloc(0.8, 35)];
const CANDS: NamedPt[] = [
  { name: 'A', x: -1, y: 0 },
  { name: 'B', x: 0, y: 0 },
  { name: 'C', x: 1, y: 0 },
];

describe('strategic equilibrium — iterated better-response', () => {
  const report = equilibriumReport(VOTERS, CANDS);
  const find = (rule: string) => report.verdicts.find((v) => v.rule === rule)!;

  it('collapses the electorate to its 3 distinct preference blocs', () => {
    expect(report.groups).toBe(3);
  });

  it('plurality: strategy shifts the winner from A to the centrist B', () => {
    const v = find('plurality');
    expect(v.sincereWinner).toBe('A');
    expect(v.equilibriumWinner).toBe('B');
    expect(v.outcome).toBe('shifted');
  });

  it('a Condorcet method elects B sincerely and holds it at equilibrium', () => {
    const v = find('condorcet');
    expect(v.sincereWinner).toBe('B');
    expect(v.equilibriumWinner).toBe('B');
    expect(v.outcome).toBe('stable');
  });

  it('random ballot is strategyproof — always stable on its sincere winner', () => {
    const v = find('random_ballot');
    expect(v.outcome).toBe('stable');
    expect(v.equilibriumWinner).toBe(v.sincereWinner);
  });
});
