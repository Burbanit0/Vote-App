// The handover from the hero to the count: the hero's map and the count's map draw the
// same electorate, so as the page scrolls from one to the other, the map itself moves
// across: its card, its voters and its candidates fly from where they sit on the
// hero to where they sit on the count, and the voters' colours fade to the count's
// grey (nobody has voted yet). Pure: given the progress and the two maps' boxes on
// screen, where everything is.

import { CANDIDATES, VOTERS } from './scenario';
import { MAP, VIEW, candidatePoint, voterPoint } from './countFrame';
import { clamp01, easeInOutCubic, lerp } from './motion';

/** A box on screen, as getBoundingClientRect gives it. */
export interface Box {
  left: number;
  top: number;
  width: number;
  height: number;
}

/**
 * How each map is drawn, shared with the components that draw them, so the flying copy
 * leaves and lands on exactly what is on screen. The hero's in its 100 × 70 viewBox; the
 * count's in its drawing's units (lib/home/countFrame.ts).
 */
export const HERO_DRAW = {
  w: 100,
  h: 70,
  voterR: 0.9,
  candR: 2.6,
  labelDy: 4.5,
  label: 3.6,
  radius: 10,
};
export const COUNT_DRAW = { voterR: 3.2, candR: 8, labelDy: 16, label: 15, radius: 12 };

/** The hero's text and tray clear away at 1.6 × the handover: gone by this point. */
export const HERO_GONE = 1 / 1.6;
/** The count's caption, box, piles and scrubber come in after this point. */
export const COUNT_IN = 0.6;

/** Scroll progress through the handover, 0 … 1. */
export function handoverProgress(scrollY: number, start: number, end: number): number {
  return clamp01((scrollY - start) / Math.max(1, end - start));
}

/** The count's drawing in a box: its viewBox, scaled to fit and centred (xMidYMid meet). */
export function countViewport(box: Box) {
  const s = Math.min(box.width / VIEW.w, box.height / VIEW.h);
  return {
    s,
    point: (x: number, y: number) => ({
      x: box.left + (box.width - VIEW.w * s) / 2 + (x - VIEW.x) * s,
      y: box.top + (box.height - VIEW.h * s) / 2 + (y - VIEW.y) * s,
    }),
  };
}

interface Disc {
  x: number;
  y: number;
  r: number;
}

export interface HandoverPose {
  card: { x: number; y: number; w: number; h: number; r: number };
  voters: Disc[];
  voterOpacity: number;
  /** How far the voters have turned grey. */
  grey: number;
  candidates: (Disc & { labelY: number; size: number })[];
}

const mix = (a: Disc, b: Disc, e: number): Disc => ({
  x: lerp(a.x, b.x, e),
  y: lerp(a.y, b.y, e),
  r: lerp(a.r, b.r, e),
});

/** Everything on the flying map at progress h, between the hero's map and the count's. */
export function handoverFrame(h: number, hero: Box, count: Box): HandoverPose {
  const e = easeInOutCubic(clamp01(h));
  const u = hero.width / HERO_DRAW.w;
  const onHero = (x: number, y: number) => ({
    x: hero.left + x * hero.width,
    y: hero.top + y * hero.height,
  });
  const vp = countViewport(count);
  const cardFrom = vp.point(MAP.x, MAP.y);
  return {
    card: {
      x: lerp(hero.left, cardFrom.x, e),
      y: lerp(hero.top, cardFrom.y, e),
      w: lerp(hero.width, MAP.w * vp.s, e),
      h: lerp(hero.height, MAP.h * vp.s, e),
      r: lerp(HERO_DRAW.radius, COUNT_DRAW.radius * vp.s, e),
    },
    voters: VOTERS.map((v, i) => {
      const to = voterPoint(i);
      return mix(
        { ...onHero(v.x, v.y), r: HERO_DRAW.voterR * u },
        { ...vp.point(to.x, to.y), r: COUNT_DRAW.voterR * vp.s },
        e
      );
    }),
    voterOpacity: lerp(0.6, 0.75, e),
    // Written from the end, so a finished handover is exactly grey.
    grey: clamp01(1 - (1 - h) / 0.45),
    candidates: CANDIDATES.map((c, i) => {
      const to = candidatePoint(i);
      const d = mix(
        { ...onHero(c.x, c.y), r: HERO_DRAW.candR * u },
        { ...vp.point(to.x, to.y), r: COUNT_DRAW.candR * vp.s },
        e
      );
      return {
        ...d,
        labelY: d.y - lerp(HERO_DRAW.labelDy * u, COUNT_DRAW.labelDy * vp.s, e),
        size: lerp(HERO_DRAW.label * u, COUNT_DRAW.label * vp.s, e),
      };
    }),
  };
}
