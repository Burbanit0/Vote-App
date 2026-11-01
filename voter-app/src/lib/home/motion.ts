import { lcg } from './scenario';

// Motion primitives for the homepage, as pure functions: the components only write
// what these return to the DOM, so every curve here is unit-tested and a scrubbed
// animation is a function of progress, never of how the user got there.

/** The three curves of the motion system (see the design canvas, "Motion"). */
export const EASE = {
  settle: 'cubic-bezier(.2,.7,.2,1)',
  ink: 'cubic-bezier(.3,1.45,.45,1)',
  fold: 'cubic-bezier(.65,0,.35,1)',
} as const;

export const clamp01 = (x: number) => Math.min(1, Math.max(0, x));
export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
export const easeInOutCubic = (t: number) =>
  t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
export const easeOutCubic = (t: number) => 1 - Math.pow(1 - t, 3);

/**
 * A drop onto a floor, 0 → 1: accelerates, hits 1, bounces twice and lands. It
 * returns exactly 0 at f = 0 and exactly 1 at f = 1, so a scrub stops on a rest pose.
 */
export function bounce(f: number): number {
  const t = clamp01(f);
  return 1 - Math.exp(-5 * t) * Math.abs(Math.cos(3.5 * Math.PI * t)) * (1 - t);
}

/**
 * The position, in digits, of one odometer column showing `v` (place 0 = units).
 * A column only rolls during the last unit before it carries, like a real counter.
 */
export function odometer(v: number, place: number): number {
  const p = 10 ** place;
  const lower = v - Math.floor(v / p) * p;
  return (Math.floor(v / p) % 10) + Math.max(0, lower - (p - 1));
}

/** One step of inertia towards `target`; snaps once within `eps` so a loop can stop. */
export function approach(cur: number, target: number, k: number, eps = 0.4): number {
  const next = cur + (target - cur) * k;
  return Math.abs(target - next) < eps ? target : next;
}

const pt = (x: number, y: number) => `${x.toFixed(1)}px ${y.toFixed(1)}px`;

/**
 * The ballot slip — the brand mark's outline (a 20 × 26 sheet with a folded corner)
 * at (x, y) — as a five-point clip-path polygon.
 */
export function slipPolygon(x: number, y: number): string {
  return `polygon(${pt(x + 1, y + 1)}, ${pt(x + 13, y + 1)}, ${pt(x + 19, y + 7)}, ${pt(x + 19, y + 25)}, ${pt(x + 1, y + 25)})`;
}

/**
 * The same five points blown up past a w × h viewport, the fold outside it, so
 * the polygon covers the screen and interpolates cleanly into `slipPolygon`.
 */
export function coverPolygon(w: number, h: number): string {
  return `polygon(${pt(-0.2 * w, -0.6 * h)}, ${pt(1.048 * w, -0.6 * h)}, ${pt(1.4 * w, -0.312 * h)}, ${pt(1.4 * w, 1.2 * h)}, ${pt(-0.2 * w, 1.2 * h)})`;
}

/** How drawn panel `i` of the moments track is, given the track's scroll progress. */
export function momentDraw(progress: number, i: number): number {
  return clamp01((progress * 4.4 - i + 0.75) / 0.6);
}

/** One ballot of the closing box: where it rests and when it starts to fall. */
export interface Drop {
  x: number;
  y: number;
  r: number;
  r0: number;
  delay: number;
}

const DROP_MS = 820;

/** 100 ballots in a 20 × 5 heap, falling row by row in a shuffled order. */
export function finaleHeap(): Drop[] {
  const rnd = lcg(5);
  return Array.from({ length: 100 }, (_, n) => {
    const col = n % 20;
    const lvl = Math.floor(n / 20);
    return {
      x: 84 + col * 13 + (rnd() - 0.5) * 4,
      y: 272 - lvl * 8 - rnd() * 2,
      r: (rnd() - 0.5) * 40,
      r0: (rnd() - 0.5) * 300,
      delay: lvl * 260 + rnd() * 240,
    };
  });
}

/** A heap ballot `t` ms after the drop started: falling from above the box, then resting. */
export function dropPose(d: Drop, t: number): { x: number; y: number; rot: number; o: number } {
  const f = clamp01((t - d.delay) / DROP_MS);
  return {
    x: d.x,
    y: -24 + (d.y + 24) * bounce(f),
    rot: lerp(d.r0, d.r, easeOutCubic(f)),
    o: f > 0 ? 1 : 0,
  };
}

/** When the last heap ballot has landed. */
export const finaleDuration = (heap: Drop[]) => Math.max(...heap.map((d) => d.delay)) + DROP_MS;
