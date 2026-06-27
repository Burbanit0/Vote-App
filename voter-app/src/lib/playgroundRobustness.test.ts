import { describe, it, expect } from 'vitest';
import { winnerDistribution } from './playgroundRobustness';
import type { NamedPt, Pt } from './playgroundVoting';

const A: NamedPt = { name: 'A', x: -0.5, y: 0 };
const B: NamedPt = { name: 'B', x: 0.5, y: 0 };
const nearA: Pt[] = [
  { x: -0.5, y: 0 },
  { x: -0.4, y: 0 },
  { x: -0.6, y: 0 },
];
const nearB: Pt[] = [
  { x: 0.5, y: 0 },
  { x: 0.4, y: 0 },
  { x: 0.6, y: 0 },
];

describe('winnerDistribution', () => {
  it('counts winner frequency across resamples', () => {
    let n = 0;
    // every 4th resample the electorate favours B → B wins 1/4 under plurality
    const sampler = (): Pt[] => (n++ % 4 === 0 ? nearB : nearA);
    const d = winnerDistribution(sampler, [A, B], 'plurality', 100, 0);
    expect(d.total).toBe(100);
    expect(d.modal).toBe('A');
    expect(d.shares.find((s) => s.name === 'A')?.count).toBe(75);
    expect(d.shares.find((s) => s.name === 'B')?.count).toBe(25);
    expect(d.modalShare).toBeCloseTo(0.75, 5);
  });

  it('unanimous electorate → a single winner at 100%', () => {
    const d = winnerDistribution(() => nearA, [A, B], 'plurality', 50, 7);
    expect(d.modal).toBe('A');
    expect(d.modalShare).toBe(1);
    expect(d.shares).toHaveLength(1);
  });

  it('empty draws → no winner', () => {
    const d = winnerDistribution(() => [], [A, B], 'plurality', 10, 0);
    expect(d.total).toBe(0);
    expect(d.modal).toBeNull();
  });
});
