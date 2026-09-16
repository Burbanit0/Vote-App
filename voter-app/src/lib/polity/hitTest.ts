/**
 * lib/polity/hitTest.ts — which citizen is under the pointer, and which is next
 * in a direction for the keyboard, pure (ADR-013).
 *
 * The canvas has no DOM node per citizen, so pointing goes through a Delaunay
 * triangulation of the drawn points (d3-delaunay's nearest-point search).
 */
import { Delaunay } from 'd3-delaunay';

export interface Located {
  id: number;
  x: number;
  y: number;
}

/** Nearest citizen within `radius` pixels of (x, y), or null. */
export function makeHitTester(
  points: readonly Located[]
): (x: number, y: number, radius: number) => number | null {
  if (points.length === 0) return () => null;
  const delaunay = Delaunay.from(
    points,
    (p) => p.x,
    (p) => p.y
  );
  return (x, y, radius) => {
    const index = delaunay.find(x, y);
    const point = points[index];
    return Math.hypot(point.x - x, point.y - y) <= radius ? point.id : null;
  };
}

export type Direction = 'up' | 'down' | 'left' | 'right';

const ARROWS: Record<string, Direction> = {
  ArrowUp: 'up',
  ArrowDown: 'down',
  ArrowLeft: 'left',
  ArrowRight: 'right',
};

export function directionOf(key: string): Direction | null {
  return ARROWS[key] ?? null;
}

/**
 * The citizen the keyboard moves to from `fromId`: among the points lying in the
 * direction (within 45° of it), the nearest; none when there is none. Starting
 * with nobody selected, any arrow picks the point nearest the map's centre.
 */
export function nearestInDirection(
  points: readonly Located[],
  fromId: number | null,
  direction: Direction,
  centre: [number, number]
): number | null {
  const from = fromId === null ? null : points.find((p) => p.id === fromId);
  if (!from) {
    return nearestTo(points, centre[0], centre[1]);
  }
  const [dx, dy] = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] }[direction];
  let best: number | null = null;
  let bestDistance = Infinity;
  for (const p of points) {
    const vx = p.x - from.x;
    const vy = p.y - from.y;
    const along = vx * dx + vy * dy;
    const across = Math.abs(vx * dy - vy * dx);
    if (p.id === from.id || along <= 0 || across > along) continue;
    const distance = Math.hypot(vx, vy);
    if (distance < bestDistance) {
      best = p.id;
      bestDistance = distance;
    }
  }
  return best;
}

function nearestTo(points: readonly Located[], x: number, y: number): number | null {
  let best: number | null = null;
  let bestDistance = Infinity;
  for (const p of points) {
    const distance = Math.hypot(p.x - x, p.y - y);
    if (distance < bestDistance) {
      best = p.id;
      bestDistance = distance;
    }
  }
  return best;
}
