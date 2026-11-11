// The homepage's one electorate: 100 voters around three candidates, counted three
// ways. The hero's tally sheet and the scrubbed count below it both read it, so the
// numbers on the page always agree. Positions are in a unit square (x right, y down);
// each view scales them to its own drawing.
//
// Voters vote sincerely and spatially, like the playground: first choice = the nearest
// candidate; the runoff opposes the two plurality leaders; approval = every candidate
// within APPROVAL_RADIUS, the first choice always included.

export type RuleId = 'plurality' | 'runoff' | 'approval';
export const RULES: RuleId[] = ['plurality', 'runoff', 'approval'];

export interface Candidate {
  name: string;
  color: string;
  x: number;
  y: number;
}

export const CANDIDATES: Candidate[] = [
  { name: 'Alice', color: '#2F5BD3', x: 0.275, y: 0.316 },
  { name: 'Carol', color: '#1E8A4C', x: 0.46, y: 0.553 },
  { name: 'Bob', color: '#C8352B', x: 0.825, y: 0.342 },
];

const CLUSTER_SIZES = [35, 21, 44];
export const APPROVAL_RADIUS = 0.36;

export interface Voter {
  x: number;
  y: number;
  /** Index of the nearest candidate. */
  first: number;
  /** Candidates within APPROVAL_RADIUS, the first choice included. */
  approves: number[];
}

export interface Tally {
  counts: number[];
  winner: number;
  /** Runoff only: the candidate eliminated after round one. */
  out?: number;
}

/** Park–Miller, as in the design canvas, so the drawing matches it. */
export function lcg(seed: number): () => number {
  let s = seed;
  return () => {
    s = (s * 16807) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

const d2 = (a: { x: number; y: number }, b: { x: number; y: number }) =>
  (a.x - b.x) ** 2 + (a.y - b.y) ** 2;

function nearest(p: { x: number; y: number }, among: number[]): number {
  return among.reduce((best, c) => (d2(p, CANDIDATES[c]) < d2(p, CANDIDATES[best]) ? c : best));
}

function buildVoters(): Voter[] {
  const rnd = lcg(11);
  // Irwin–Hall(3) centred: a cheap, bounded bell.
  const g = () => rnd() + rnd() + rnd() - 1.5;
  const clamp = (v: number) => Math.max(0.03, Math.min(0.97, v));
  const out: Voter[] = [];
  CANDIDATES.forEach((c, ci) => {
    for (let i = 0; i < CLUSTER_SIZES[ci]; i++) {
      const p = { x: clamp(c.x + g() * 0.175), y: clamp(c.y + g() * 0.153) };
      const first = nearest(p, [0, 1, 2]);
      const approves = [0, 1, 2].filter(
        (k) => k === first || d2(p, CANDIDATES[k]) <= APPROVAL_RADIUS ** 2
      );
      out.push({ ...p, first, approves });
    }
  });
  return out;
}

export const VOTERS: Voter[] = buildVoters();

const argmax = (xs: number[]) => xs.indexOf(Math.max(...xs));

function plurality(): Tally {
  const counts = [0, 0, 0];
  VOTERS.forEach((v) => (counts[v.first] += 1));
  return { counts, winner: argmax(counts) };
}

const FIRST_COUNTS = plurality().counts;
/** Round-one leaders, best first, and the candidate they leave out. */
const [LEAD_A, LEAD_B, OUT] = [0, 1, 2].sort((p, q) => FIRST_COUNTS[q] - FIRST_COUNTS[p]);

/** Where each voter's ballot sits in the runoff: their first choice if still in, else the nearer finalist. */
export const RUNOFF_CHOICE: number[] = VOTERS.map((v) =>
  v.first === OUT ? nearest(v, [LEAD_A, LEAD_B]) : v.first
);

function runoff(): Tally {
  const counts = [0, 0, 0];
  RUNOFF_CHOICE.forEach((c) => (counts[c] += 1));
  return { counts, winner: argmax(counts), out: OUT };
}

function approval(): Tally {
  const counts = [0, 0, 0];
  VOTERS.forEach((v) => v.approves.forEach((c) => (counts[c] += 1)));
  return { counts, winner: argmax(counts) };
}

export const TALLY: Record<RuleId, Tally> = {
  plurality: plurality(),
  runoff: runoff(),
  approval: approval(),
};

/** A rule's counts by candidate name, for the copy: {{alice}}, {{carol}}, {{bob}}. */
export const countsByName = (rule: RuleId) =>
  Object.fromEntries(CANDIDATES.map((c, i) => [c.name.toLowerCase(), TALLY[rule].counts[i]]));
