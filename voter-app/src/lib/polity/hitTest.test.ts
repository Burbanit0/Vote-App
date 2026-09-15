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
    expect(makeHitTester([])(0, 0, 10)).toBeNull();
  });

  it('moves the keyboard selection to the nearest citizen in a direction', () => {
    expect(nearestInDirection(POINTS, 0, 'right', [0, 0])).toBe(1);
    expect(nearestInDirection(POINTS, 0, 'down', [0, 0])).toBe(2);
    expect(nearestInDirection(POINTS, 0, 'left', [0, 0])).toBe(3);
    expect(nearestInDirection(POINTS, 0, 'up', [0, 0])).toBe(4);
    expect(nearestInDirection(POINTS, 1, 'right', [0, 0])).toBeNull();
    expect(nearestInDirection(POINTS, null, 'up', [52, 48])).toBe(0);
    expect(nearestInDirection(POINTS, 99, 'up', [101, 49])).toBe(1);
    expect(nearestInDirection([], null, 'up', [0, 0])).toBeNull();
  });

  it('reads arrow keys as directions', () => {
    expect(directionOf('ArrowUp')).toBe('up');
    expect(directionOf('ArrowLeft')).toBe('left');
    expect(directionOf('Enter')).toBeNull();
  });
});
