import { describe, it, expect } from 'vitest';
import { summarizeMap } from './mapSummary';

const CANDS = [
  { name: 'A', x: -0.6, y: 0.04, z: 0.3 },
  { name: 'B', x: 0.6, y: -0.04 },
];

describe('summarizeMap: the leader map in words', () => {
  it('gives each candidate its place on the axes the map shows, and its first-choice share', () => {
    const voters = [
      { x: -0.5, y: 0 },
      { x: -0.7, y: 0.1 },
      { x: 0.5, y: 0 },
    ];
    expect(summarizeMap(voters, CANDS, 2)).toEqual([
      { name: 'A', position: '(-0.6, 0.0)', firstChoicePct: 67 },
      { name: 'B', position: '(0.6, 0.0)', firstChoicePct: 33 },
    ]);
    expect(summarizeMap(voters, CANDS, 1)[0].position).toBe('(-0.6)');
    expect(summarizeMap(voters, CANDS, 3)[1].position).toBe('(0.6, 0.0, 0.0)');
  });

  it('reads 0% for everyone when there are no voters', () => {
    expect(summarizeMap([], CANDS, 2).map((c) => c.firstChoicePct)).toEqual([0, 0]);
  });
});
