import { describe, it, expect } from 'vitest';
import { nearestCandidate } from './identityGroups';
import { drawName } from './tieLot';

const LEFT_TO_RIGHT = [
  { name: 'Alice', x: -0.5 },
  { name: 'Bob', x: 0.0 },
  { name: 'Carol', x: 0.5 },
];

describe('nearestCandidate', () => {
  it('is the candidate nearest the centre', () => {
    // The three default groups' centres.
    expect(nearestCandidate(LEFT_TO_RIGHT, -0.3, 0)).toBe('Alice');
    expect(nearestCandidate(LEFT_TO_RIGHT, 0.1, 0)).toBe('Bob');
    expect(nearestCandidate(LEFT_TO_RIGHT, 0.4, 0)).toBe('Carol');
  });

  it('does not follow the order the candidates are listed in', () => {
    for (const listing of [
      [...LEFT_TO_RIGHT].reverse(),
      [...LEFT_TO_RIGHT.slice(1), LEFT_TO_RIGHT[0]],
    ]) {
      expect(nearestCandidate(listing, -0.3, 0)).toBe('Alice');
      expect(nearestCandidate(listing, 0.4, 0)).toBe('Carol');
    }
  });

  it.each([0, 1, 2, 3, 7])(
    'draws an exact tie by the seeded lot over the names (seed %i)',
    (seed) => {
      // -0.5 and -0.1 are both 0.2 from -0.3.
      const pair = [
        { name: 'Alice', x: -0.5 },
        { name: 'Bob', x: -0.1 },
      ];
      const drawn = drawName(['Alice', 'Bob'], seed); // the backend's tie_lot.draw, pinned in tieLot.test.ts
      expect(nearestCandidate(pair, -0.3, seed)).toBe(drawn);
      expect(nearestCandidate([...pair].reverse(), -0.3, seed)).toBe(drawn);
    }
  );

  it('does not draw when one candidate is nearer', () => {
    const pair = [
      { name: 'Alice', x: -0.5 },
      { name: 'Bob', x: -0.1 },
    ];
    for (let seed = 0; seed < 8; seed++) expect(nearestCandidate(pair, -0.4, seed)).toBe('Alice');
  });
});
