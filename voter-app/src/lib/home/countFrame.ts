// The scrubbed count: 100 voters cast their ballots into a box, the ballots are
// sorted into tally piles, the runoff moves the eliminated candidate's ballots, and
// approval adds the extra approvals. Everything is a pure function of the count's
// scroll progress P (0 … 5, one unit per screen), so scrolling back up retraces it
// exactly. Drawn in a 1000 × 640 viewBox: the map on the left, the box in the
// middle, a pile per candidate on the right.

import {
  APPROVAL_RADIUS,
  CANDIDATES,
  RUNOFF_CHOICE,
  TALLY,
  VOTERS,
  lcg,
  type RuleId,
} from './scenario';
import { bounce, clamp01, easeInOutCubic as ease, lerp } from './motion';

export const MAP = { x: 40, y: 160, w: 400, h: 380 };
/** The part of the 1000 × 640 drawing on screen: nothing flies higher than y = 90. */
export const VIEW = { x: 0, y: 90, w: 1000, h: 550 };
/** Where ballots go into the box. */
const SLOT = { x: 560, y: 292 };
export const PILE_X = [690, 800, 910];
export const STEPS = 5;

export const voterPoint = (i: number) => ({
  x: MAP.x + VOTERS[i].x * MAP.w,
  y: MAP.y + VOTERS[i].y * MAP.h,
});
export const candidatePoint = (c: number) => ({
  x: MAP.x + CANDIDATES[c].x * MAP.w,
  y: MAP.y + CANDIDATES[c].y * MAP.h,
});

interface Ballot {
  voter: number;
  cand: number;
  /** Position in its pile. */
  k: number;
  spin: number;
  /** A first-choice ballot that changes pile in the runoff. */
  move?: { cand: number; k: number };
  /** Resting place in the box (first-choice ballots only). */
  rest: { x: number; y: number; r: number };
  dA: number;
  dB: number;
  dC: number;
  /** An approval ballot, cast in the last chapter. */
  extra: boolean;
}

function build(): Ballot[] {
  const rnd = lcg(11);
  const spin = () => (rnd() < 0.5 ? -1 : 1) * (120 + rnd() * 160);
  const kOf = [0, 0, 0];
  const firsts: Ballot[] = VOTERS.map((v, i) => ({
    voter: i,
    cand: v.first,
    k: kOf[v.first]++,
    spin: spin(),
    rest: { x: 0, y: 0, r: (rnd() - 0.5) * 50 },
    dA: v.x * 0.55,
    dB: rnd() * 0.5,
    dC: rnd() * 0.5,
    extra: false,
  }));
  // The box fills as a heap, in the order ballots arrive.
  [...firsts]
    .sort((a, b) => a.dA - b.dA)
    .forEach((b, n) => {
      const jitter = rnd();
      b.rest.x = 514 + (n % 8) * 13 + (jitter - 0.5) * 6;
      b.rest.y = 460 - Math.floor(n / 8) * 5.4 - jitter * 2;
    });
  const movedTo = [0, 0, 0];
  firsts.forEach((b) => {
    const to = RUNOFF_CHOICE[b.voter];
    if (to !== b.cand) b.move = { cand: to, k: TALLY.plurality.counts[to] + movedTo[to]++ };
  });
  const extraOf = [0, 0, 0];
  const extras: Ballot[] = [];
  VOTERS.forEach((v, i) =>
    v.approves
      .filter((c) => c !== v.first)
      .forEach((c) =>
        extras.push({
          voter: i,
          cand: c,
          k: TALLY.plurality.counts[c] + extraOf[c]++,
          spin: spin(),
          rest: { x: 0, y: 0, r: 0 },
          dA: 0,
          dB: 0,
          dC: v.x * 0.4 + rnd() * 0.1,
          extra: true,
        })
      )
  );
  return [...firsts, ...extras];
}

export const BALLOTS: Ballot[] = build();

/**
 * Where a candidate's approvals come from: every voter within APPROVAL_RADIUS of them,
 * which the map's 400 × 380 stretch draws as a slight ellipse.
 */
export function approvalArea(c: number) {
  const p = candidatePoint(c);
  return { cx: p.x, cy: p.y, rx: APPROVAL_RADIUS * MAP.w, ry: APPROVAL_RADIUS * MAP.h };
}

/** A tally mark's place: four strokes, then the fifth across them. */
export function pileSlot(cand: number, k: number) {
  const col = k % 5;
  const y = 545 - Math.floor(k / 5) * 18 - 7;
  if (col === 4) return { x: PILE_X[cand], y, r: 62, w: 2.2, h: 46 };
  return { x: PILE_X[cand] - 18 + col * 12, y, r: 0, w: 2.2, h: 14 };
}

/** Where a rule's "Elected" stamp sits: just above the winner's pile. */
export function stampPoint(rule: RuleId) {
  const t = TALLY[rule];
  return { x: PILE_X[t.winner], y: 545 - Math.ceil(t.counts[t.winner] / 5) * 18 - 34 };
}

interface Pose {
  x: number;
  y: number;
  w: number;
  h: number;
  rot: number;
  fill: string;
  o: number;
  sw: number;
}

export interface CountFrame {
  ballots: Pose[];
  /** Voters whose ballot has left their hand (they light up in their colour). */
  lit: boolean[];
  /** Ballots through the slot. */
  cast: number;
  /** Ballots resting on each pile. */
  landed: number[];
  /** How far each candidate's approval area has opened, 0 … 1 (see approvalArea). */
  areas: number[];
  /** How far the box jolts down, in px, from ballots hitting the heap. */
  jolt: number;
  /** The chapter the count is closest to, 0 … STEPS. */
  step: number;
  /** Whose result is decided right now, if anyone's. */
  stamp: RuleId | null;
}

const hex = (h: string) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
function mix(a: string, b: string, t: number): string {
  const x = hex(a);
  const y = hex(b);
  return `rgb(${x.map((v, i) => Math.round(lerp(v, y[i], t))).join(',')})`;
}

function bez(
  a: { x: number; y: number },
  c: { x: number; y: number },
  b: { x: number; y: number },
  s: number
) {
  const u = 1 - s;
  return {
    x: u * u * a.x + 2 * u * s * c.x + s * s * b.x,
    y: u * u * a.y + 2 * u * s * c.y + s * s * b.y,
  };
}

const WHITE = '#FFFFFF';
/** Share of the cast flight spent in the air before the slot; the rest is the drop. */
const AIR = 0.72;
const color = (c: number) => CANDIDATES[c].color;

/** A phase's progress, 0 … 1, for one ballot with its own delay. */
type Raw = (start: number, end: number, delay: number, dur: number) => number;
/** What a frame has counted, filled in as its ballots are posed. */
interface Tallies {
  landed: number[];
  cast: number;
  jolt: number;
}

/** An approval ballot: from the voter straight onto its pile. */
function approvalPose(b: Ballot, raw: Raw, n: Tallies): Pose {
  const v = voterPoint(b.voter);
  const s = ease(raw(3.15, 4.0, b.dC, 0.5));
  const dst = pileSlot(b.cand, b.k);
  const m = clamp01((s - 0.55) / 0.45);
  if (s === 1) n.landed[b.cand]++;
  return {
    ...bez(v, { x: (v.x + dst.x) / 2, y: 110 }, dst, s),
    w: lerp(13, dst.w, m),
    h: lerp(8, dst.h, m),
    rot: lerp(b.spin, dst.r, m),
    fill: mix(WHITE, color(b.cand), m),
    o: Math.min(1, s * 5),
    sw: 0.9 * (1 - m),
  };
}

/** Cast: in the air to the slot, turning edge-on, then a damped bounce onto the heap. */
function castPose(b: Ballot, a: number, n: Tallies): Pose {
  if (a < AIR) {
    const v = voterPoint(b.voter);
    const s = ease(a / AIR);
    return {
      ...bez(v, { x: (v.x + SLOT.x) / 2, y: 120 }, SLOT, s),
      w: 13,
      h: 8,
      rot: lerp(b.spin, 90, s),
      fill: WHITE,
      o: Math.min(1, a * 8),
      sw: 0.9,
    };
  }
  const f = (a - AIR) / (1 - AIR);
  if (f > 0.1 && f < 0.2) n.jolt++;
  return {
    x: lerp(SLOT.x, b.rest.x, 1 - (1 - f) * (1 - f)),
    y: SLOT.y + (b.rest.y - SLOT.y) * bounce(f),
    w: 13,
    h: 8,
    rot: lerp(90, b.rest.r, 1 - Math.pow(1 - f, 3)),
    fill: WHITE,
    o: 1,
    sw: 0.9,
  };
}

/** Sorted from the box onto its first-choice pile. */
function sortPose(b: Ballot, sB: number, n: Tallies): Pose {
  const own = pileSlot(b.cand, b.k);
  const m = clamp01((sB - 0.55) / 0.45);
  if (sB === 1) n.landed[b.cand]++;
  return {
    ...bez(b.rest, { x: (b.rest.x + own.x) / 2, y: 220 }, own, sB),
    w: lerp(13, own.w, m),
    h: lerp(8, own.h, m),
    rot: lerp(b.rest.r, own.r, m),
    fill: mix(WHITE, color(b.cand), m),
    o: 1,
    sw: 0.9 * (1 - m),
  };
}

/** The runoff moves it to the finalist this voter prefers; approval moves it back. */
function movePose(
  b: Ballot,
  move: { cand: number; k: number },
  sC: number,
  sD: number,
  n: Tallies
): Pose {
  const own = pileSlot(b.cand, b.k);
  const to = pileSlot(move.cand, move.k);
  const going = sD === 0;
  const s = going ? sC : sD;
  const [from, dst] = going ? [own, to] : [to, own];
  const [c0, c1] = going ? [b.cand, move.cand] : [move.cand, b.cand];
  const m = 1 - Math.sin(Math.PI * s);
  const near = s < 0.5 ? from : dst;
  if (s === 1) n.landed[c1]++;
  return {
    ...bez(from, { x: (own.x + to.x) / 2, y: 190 }, dst, s),
    w: lerp(13, near.w, m),
    h: lerp(8, near.h, m),
    rot: lerp(near.r, (b.spin > 0 === going ? 1 : -1) * 160, 1 - m),
    fill: mix(color(c0), color(c1), s),
    o: 1,
    sw: 0.9 * (1 - m),
  };
}

/** A first-choice ballot, through all four chapters. */
function firstPose(b: Ballot, raw: Raw, n: Tallies): Pose {
  const a = raw(0.35, 1.0, b.dA, 0.45);
  const sB = ease(raw(1.15, 2.0, b.dB, 0.5));
  const sC = b.move ? ease(raw(2.15, 3.0, b.dC, 0.5)) : 0;
  const sD = b.move ? ease(raw(3.15, 4.0, b.dC, 0.5)) : 0;
  if (a >= AIR) n.cast++;
  if (sB === 0) return castPose(b, a, n);
  if (sC === 0) return sortPose(b, sB, n);
  return movePose(b, b.move!, sC, sD, n);
}

/** Whose result is decided at this point of the count, if anyone's. */
function decided(P: number): RuleId | null {
  if (P >= 3.9) return 'approval';
  if (P >= 2.9 && P < 3.6) return 'runoff';
  if (P >= 1.9 && P < 2.6) return 'plurality';
  return null;
}

export function countFrame(P: number): CountFrame {
  const raw: Raw = (start, end, delay, dur) => clamp01(((P - start) / (end - start) - delay) / dur);
  const n: Tallies = { landed: [0, 0, 0], cast: 0, jolt: 0 };
  const ballots = BALLOTS.map((b) => (b.extra ? approvalPose(b, raw, n) : firstPose(b, raw, n)));
  return {
    ballots,
    lit: BALLOTS.slice(0, VOTERS.length).map((b) => raw(0.35, 1.0, b.dA, 0.45) > 0.02),
    cast: n.cast,
    landed: n.landed,
    // One after the other, so each candidate's reach reads on its own before they overlap.
    areas: CANDIDATES.map((_, c) => ease(raw(3.15, 4.0, c * 0.15, 0.7))),
    jolt: Math.min(3, n.jolt * 0.7),
    step: Math.round(clamp01(P / STEPS) * STEPS),
    stamp: decided(P),
  };
}

/** A caption's opacity and lift: caption 0 fades out as the count starts, the others peak at their chapter. */
export function captionPose(P: number, i: number): { o: number; y: number } {
  if (i === 0) return { o: clamp01(1 - P / 0.3), y: -P * 60 };
  return { o: clamp01(1 - Math.abs(P - (i - 0.15)) * 2.2), y: (i - 0.15 - P) * 36 };
}
