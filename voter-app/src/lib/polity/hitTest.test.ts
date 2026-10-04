import { directionOf, makeHitTester, nearestInDirection } from './hitTest';

const POINTS = [
  { id: 0, x: 50, y: 50 },
  { id: 1, x: 100, y: 50 },
  { id: 2, x: 50, y: 100 },
  { id: 3, x: 0, y: 55 },
  { id: 4, x: 60, y: 0 },
];

describe('hit testing', () => {
  it('finds the citizen under the pointer, within a radius', () => {
    const hit = makeHitTester(POINTS);
    expect(hit(98, 52, 6)).toBe(1);
    expect(hit(75, 75, 6)).toBeNull();
    // Unbounded, it is the nearest citizen anywhere: where the map's arrows start from.
    expect(hit(52, 48, Infinity)).toBe(0);
    expect(hit(101, 49, Infinity)).toBe(1);
    expect(makeHitTester([])(0, 0, 10)).toBeNull();
  });

  it('moves the keyboard selection to the nearest citizen in a direction', () => {
    expect(nearestInDirection(POINTS, 0, 'right')).toBe(1);
    expect(nearestInDirection(POINTS, 0, 'down')).toBe(2);
    expect(nearestInDirection(POINTS, 0, 'left')).toBe(3);
    expect(nearestInDirection(POINTS, 0, 'up')).toBe(4);
    expect(nearestInDirection(POINTS, 1, 'right')).toBeNull();
    expect(nearestInDirection(POINTS, 99, 'up')).toBeNull();
    expect(nearestInDirection([], 0, 'up')).toBeNull();
  });

  it('reads arrow keys as directions', () => {
    expect(directionOf('ArrowUp')).toBe('up');
    expect(directionOf('ArrowLeft')).toBe('left');
    expect(directionOf('Enter')).toBeNull();
  });
});
