// discoverVoteAnim.ts — the twelve-friends profile and the per-method "how the
// count unfolds" frames that drive the /decouvrir animation. Everything here is
// computed from the SAME ballots, so the animation can't disagree with the real
// engine (discoverVoteAnim.test.ts locks the final leader of each method's frames
// to ruleWinnerFromRanks). A frame is a still; the component tweens between them.

import type { Rule } from './playgroundVoting';

// Pizza=0, Sushi=1, Thaï=2 — a genuine centre-squeeze among 12 friends.
export const GROUPS = [
  { n: 5, rank: [0, 2, 1], approve: [1, 0, 1] }, // 🍕 › 🍜 › 🍣  (approuve Pizza + Thaï)
  { n: 4, rank: [1, 2, 0], approve: [0, 1, 1] }, // 🍣 › 🍜 › 🍕  (approuve Sushi + Thaï)
  { n: 3, rank: [2, 1, 0], approve: [0, 1, 1] }, // 🍜 › 🍣 › 🍕  (approuve Thaï + Sushi)
];
export const FOOD_COUNT = 3;
export const ELECTORATE = GROUPS.reduce((s, g) => s + g.n, 0); // 12

export const RANKS: number[][] = [];
export const SCORES: number[][] = [];
for (const g of GROUPS)
  for (let i = 0; i < g.n; i++) {
    RANKS.push(g.rank);
    SCORES.push(g.approve);
  }

// ── Tallies, computed from the ballots (never hand-typed) ─────────────────────
const firstChoiceCounts = (): number[] => {
  const c = new Array(FOOD_COUNT).fill(0);
  for (const r of RANKS) c[r[0]]++;
  return c;
};

/** Voters preferring `a` over `b` (a appears earlier in the ranking). */
const prefers = (a: number, b: number): number =>
  RANKS.filter((r) => r.indexOf(a) < r.indexOf(b)).length;

const approvalCounts = (): number[] => {
  const c = new Array(FOOD_COUNT).fill(0);
  for (const s of SCORES) s.forEach((v, i) => (c[i] += v));
  return c;
};

/** Top-two runoff: first-choice leaders, everyone else transfers to their
 *  preferred of the two. Returns per-candidate seats plus who was eliminated. */
const runoff = (): { counts: number[]; eliminated: number[] } => {
  const fc = firstChoiceCounts();
  const order = fc.map((_, i) => i).sort((x, y) => fc[y] - fc[x]);
  const [a, b] = [order[0], order[1]];
  const counts = new Array(FOOD_COUNT).fill(0);
  for (const r of RANKS) counts[r.indexOf(a) < r.indexOf(b) ? a : b]++;
  const eliminated = order.slice(2);
  return { counts, eliminated };
};

// ── Frames ────────────────────────────────────────────────────────────────────
export interface TallyBar {
  food: number;
  value: number;
  eliminated?: boolean;
}
export interface TallyFrame {
  kind: 'tally';
  captionKey: string;
  bars: TallyBar[];
}
export interface Duel {
  /** `left` is always the candidate the story follows (Thaï). */
  left: number;
  right: number;
  leftVotes: number;
  rightVotes: number;
}
export interface DuelFrame {
  kind: 'duel';
  captionKey: string;
  duels: Duel[];
}
export type Frame = TallyFrame | DuelFrame;

const bars = (counts: number[], eliminated: number[] = []): TallyBar[] =>
  counts.map((value, food) => ({ food, value, eliminated: eliminated.includes(food) }));

const THAI = 2;
const duel = (opp: number): Duel => ({
  left: THAI,
  right: opp,
  leftVotes: prefers(THAI, opp),
  rightVotes: prefers(opp, THAI),
});

/** The ordered stills for a method. The component tweens bar widths between
 *  consecutive frames — so a two-round frame that drops Thaï to 0 and lifts
 *  Sushi reads as an actual transfer, not two unrelated bar charts. */
export function voteFrames(rule: Rule): Frame[] {
  const fc = firstChoiceCounts();
  switch (rule) {
    case 'two_round': {
      const { counts, eliminated } = runoff();
      return [
        { kind: 'tally', captionKey: 'discover.anim.tr1', bars: bars(fc) },
        { kind: 'tally', captionKey: 'discover.anim.tr2', bars: bars(counts, eliminated) },
      ];
    }
    case 'approval':
      return [
        { kind: 'tally', captionKey: 'discover.anim.ap1', bars: bars(fc) },
        { kind: 'tally', captionKey: 'discover.anim.ap2', bars: bars(approvalCounts()) },
      ];
    case 'condorcet':
      return [
        { kind: 'duel', captionKey: 'discover.anim.cd1', duels: [duel(0)] },
        { kind: 'duel', captionKey: 'discover.anim.cd2', duels: [duel(0), duel(1)] },
      ];
    case 'plurality':
    default:
      return [{ kind: 'tally', captionKey: 'discover.anim.plurality', bars: bars(fc) }];
  }
}

/** The candidate a method's animation ends on — asserted == the engine winner. */
export function frameWinner(rule: Rule): number {
  const frames = voteFrames(rule);
  const last = frames[frames.length - 1];
  if (last.kind === 'tally') {
    return last.bars.reduce((best, b) => (b.value > last.bars[best].value ? b.food : best), 0);
  }
  // Condorcet: the candidate that wins every duel shown (Thaï, by construction).
  return last.duels.every((d) => d.leftVotes > d.rightVotes) ? last.duels[0].left : -1;
}
