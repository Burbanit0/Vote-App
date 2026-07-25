// voteTrace.ts — step-by-step REPLAYS of each voting rule, for the "how does it
// work?" animation. These are illustrative traces (one frame = one animation
// beat) over a SHARED sample of ballots; the authoritative winner always comes
// from ruleWinnerFromRanks (the parity-locked engine), never re-derived here —
// so a trace can never disagree with the Bilan table. Tests assert that.
//
// The 17 rules collapse into 5 visual families, all rendered by ONE component as
// animated horizontal bars + a caption:
//   count     — one ballot at a time drops onto a bar (plurality/approval/score/borda)
//   elim      — one round at a time, a candidate is knocked out (irv/two_round/…)
//   pairwise  — one duel at a time fills the tournament (Condorcet methods)
//   twophase  — score everyone, then a final runoff (STAR / majority judgment)
//   lottery   — draw a single ballot (random ballot)

import {
  computeRanks,
  computeScores,
  ruleWinnerFromRanks,
  smithSet,
  condorcetWinnerIdx,
  CARDINAL_RULES,
  type Rule,
  type Pt,
  type NamedPt,
} from './playgroundVoting';

export type TraceFamily = 'count' | 'elim' | 'pairwise' | 'twophase' | 'lottery';

/** i18n-deferred caption: the component runs t(key, params). */
export interface TraceCaption {
  key: string;
  params?: Record<string, string | number>;
}

export interface TraceFrame {
  caption: TraceCaption;
  /** Bar value per candidate index (same length/order as cands). */
  bars: number[];
  /** Greyed-out (knocked-out) candidates. */
  eliminated?: boolean[];
  /** Candidate indices to emphasise this beat (the duel pair, finalists, winner). */
  highlight?: number[];
}

export interface VoteTrace {
  family: TraceFamily;
  rule: Rule;
  frames: TraceFrame[];
  /** Authoritative winner index (from the engine). */
  winner: number;
  /** i18n key for the bar unit label (votes / points / duels / grade). */
  unitKey: string;
  sampleSize: number;
}

export const FAMILY_OF: Record<Rule, TraceFamily> = {
  plurality: 'count',
  approval: 'count',
  score: 'count',
  borda: 'count',
  two_round: 'elim',
  irv: 'elim',
  coombs: 'elim',
  nanson: 'elim',
  baldwin: 'elim',
  bucklin: 'elim',
  condorcet: 'pairwise',
  minimax: 'pairwise',
  schulze: 'pairwise',
  ranked_pairs: 'pairwise',
  star: 'twophase',
  majority_judgment: 'twophase',
  random_ballot: 'lottery',
  anti_plurality: 'count',
  dowdall: 'count',
  black: 'pairwise',
  smith_irv: 'elim',
  split_cycle: 'pairwise',
  kemeny: 'pairwise',
  cumulative: 'count',
  maximin: 'count',
  benham: 'elim',
  river: 'pairwise',
  nash: 'count',
  raynaud: 'elim',
};

const UNIT_OF: Record<Rule, string> = {
  plurality: 'replay.unit.votes',
  two_round: 'replay.unit.votes',
  irv: 'replay.unit.votes',
  coombs: 'replay.unit.votes',
  bucklin: 'replay.unit.votes',
  approval: 'replay.unit.votes',
  random_ballot: 'replay.unit.votes',
  borda: 'replay.unit.points',
  score: 'replay.unit.points',
  nanson: 'replay.unit.points',
  baldwin: 'replay.unit.points',
  star: 'replay.unit.points',
  condorcet: 'replay.unit.duels',
  minimax: 'replay.unit.duels',
  schulze: 'replay.unit.duels',
  ranked_pairs: 'replay.unit.duels',
  majority_judgment: 'replay.unit.grade',
  anti_plurality: 'replay.unit.points',
  dowdall: 'replay.unit.points',
  black: 'replay.unit.duels',
  smith_irv: 'replay.unit.votes',
  split_cycle: 'replay.unit.duels',
  kemeny: 'replay.unit.duels',
  cumulative: 'replay.unit.points',
  maximin: 'replay.unit.points',
  benham: 'replay.unit.votes',
  river: 'replay.unit.duels',
  nash: 'replay.unit.points',
  raynaud: 'replay.unit.duels',
};

// ── Seeded sampler (shared across all methods within one modal session) ─────────
function mulberry32(seed: number): () => number {
  return () => {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** A deterministic (seeded) subset of at most `n` voters — same seed ⇒ same sample. */
export function sampleVoters(voters: Pt[], n: number, seed: number): Pt[] {
  if (voters.length <= n) return voters.slice();
  const rnd = mulberry32(seed);
  const idx = voters.map((_, i) => i);
  for (let i = 0; i < n; i++) {
    const j = i + Math.floor(rnd() * (idx.length - i));
    [idx[i], idx[j]] = [idx[j], idx[i]];
  }
  return idx.slice(0, n).map((i) => voters[i]);
}

// ── Shared helpers ──────────────────────────────────────────────────────────
function argmax(a: number[]): number {
  let b = 0;
  for (let i = 1; i < a.length; i++) if (a[i] > a[b]) b = i;
  return b;
}

function firstPrefs(ranks: number[][], alive: boolean[], m: number): number[] {
  const c = new Array(m).fill(0);
  for (const r of ranks) {
    const t = r.find((i) => alive[i]);
    if (t !== undefined) c[t] += 1;
  }
  return c;
}

function lastPrefs(ranks: number[][], alive: boolean[], m: number): number[] {
  const last = new Array(m).fill(0);
  for (const r of ranks) {
    for (let k = r.length - 1; k >= 0; k--)
      if (alive[r[k]]) {
        last[r[k]] += 1;
        break;
      }
  }
  return last;
}

function bordaAlive(ranks: number[][], alive: boolean[], m: number): number[] {
  const k = alive.filter(Boolean).length;
  const score = new Array(m).fill(0);
  for (const r of ranks) {
    let rank = 0;
    for (const c of r)
      if (alive[c]) {
        score[c] += k - 1 - rank;
        rank += 1;
      }
  }
  return score;
}

/** Winner index among alive if it holds a strict majority of first prefs, else -1. */
function fpMajority(bars: number[], alive: boolean[]): number {
  const total = bars.reduce((s, c) => s + c, 0);
  let leader = -1;
  for (let i = 0; i < bars.length; i++)
    if (alive[i] && (leader < 0 || bars[i] > bars[leader])) leader = i;
  return leader >= 0 && bars[leader] > total / 2 ? leader : -1;
}

// ── count ─────────────────────────────────────────────────────────────────────
function traceCount(
  cands: NamedPt[],
  ranks: number[][],
  scores: number[][],
  rule: Rule,
  m: number
): TraceFrame[] {
  // Maximin tracks a running MIN (worst rating so far), so it starts at the top.
  const bars = new Array(m).fill(rule === 'maximin' ? 1 : 0);
  // Nash shows the running geometric mean of ratings (product in log-space).
  const nashAcc = new Array(m).fill(0);
  const frames: TraceFrame[] = [{ caption: { key: 'replay.count.start' }, bars: bars.slice() }];
  ranks.forEach((r, vi) => {
    const params: Record<string, string | number> = { n: vi + 1 };
    let key = 'replay.count.plurality';
    if (rule === 'plurality') {
      bars[r[0]] += 1;
      params.cand = cands[r[0]].name;
    } else if (rule === 'borda') {
      r.forEach((c, rank) => (bars[c] += m - 1 - rank));
      key = 'replay.count.borda';
      params.cand = cands[r[0]].name;
    } else if (rule === 'approval') {
      const approved: string[] = [];
      for (let i = 0; i < m; i++)
        if (scores[vi][i] >= 0.5) {
          bars[i] += 1;
          approved.push(cands[i].name);
        }
      key = 'replay.count.approval';
      params.cand = approved.join(', ') || '—';
    } else if (rule === 'anti_plurality') {
      const lastIdx = r[m - 1];
      for (let i = 0; i < m; i++) if (i !== lastIdx) bars[i] += 1;
      key = 'replay.count.antiPlurality';
      params.cand = cands[lastIdx].name;
    } else if (rule === 'dowdall') {
      r.forEach((c, rank) => (bars[c] += 1 / (rank + 1)));
      key = 'replay.count.dowdall';
      params.cand = cands[r[0]].name;
    } else if (rule === 'cumulative') {
      const sum = scores[vi].reduce((a, x) => a + x, 0);
      if (sum > 0) for (let i = 0; i < m; i++) bars[i] += scores[vi][i] / sum;
      key = 'replay.count.cumulative';
      params.cand = cands[r[0]].name;
    } else if (rule === 'maximin') {
      for (let i = 0; i < m; i++) bars[i] = Math.min(bars[i], scores[vi][i]);
      key = 'replay.count.maximin';
      params.cand = cands[r[m - 1]].name;
    } else if (rule === 'nash') {
      for (let i = 0; i < m; i++) {
        nashAcc[i] += Math.log(Math.max(scores[vi][i], 1e-6));
        bars[i] = Math.exp(nashAcc[i] / (vi + 1)); // geometric mean so far
      }
      key = 'replay.count.nash';
      params.cand = cands[r[0]].name;
    } else {
      // score
      for (let i = 0; i < m; i++) bars[i] += Math.round(scores[vi][i] * 5);
      key = 'replay.count.score';
      params.cand = cands[r[0]].name;
    }
    frames.push({ caption: { key, params }, bars: bars.slice() });
  });
  const w = argmax(bars);
  frames.push({
    caption: { key: 'replay.count.done', params: { cand: cands[w].name } },
    bars: bars.slice(),
    highlight: [w],
  });
  return frames;
}

// ── elim ────────────────────────────────────────────────────────────────────
interface ElimSpec {
  bars: (ranks: number[][], alive: boolean[], m: number) => number[];
  doomed: (ranks: number[][], alive: boolean[], m: number, bars: number[]) => number[];
  majority: boolean; // short-circuit when a first-pref majority appears
  roundKey: string;
}

const ELIM_SPECS: Partial<Record<Rule, ElimSpec>> = {
  irv: {
    bars: firstPrefs,
    majority: true,
    roundKey: 'replay.elim.irvRound',
    doomed: (_r, alive, m, bars) => {
      let min = Infinity;
      for (let i = 0; i < m; i++) if (alive[i] && bars[i] < min) min = bars[i];
      const d: number[] = [];
      for (let i = 0; i < m; i++) if (alive[i] && bars[i] === min) d.push(i);
      return d;
    },
  },
  coombs: {
    bars: firstPrefs,
    majority: true,
    roundKey: 'replay.elim.coombsRound',
    doomed: (ranks, alive, m) => {
      const last = lastPrefs(ranks, alive, m);
      let max = -1;
      for (let i = 0; i < m; i++) if (alive[i] && last[i] > max) max = last[i];
      const d: number[] = [];
      for (let i = 0; i < m; i++) if (alive[i] && last[i] === max) d.push(i);
      return d;
    },
  },
  nanson: {
    bars: bordaAlive,
    majority: false,
    roundKey: 'replay.elim.nansonRound',
    doomed: (_r, alive, m, bars) => {
      const idx = [];
      for (let i = 0; i < m; i++) if (alive[i]) idx.push(i);
      const avg = idx.reduce((s, i) => s + bars[i], 0) / idx.length;
      return idx.filter((i) => bars[i] < avg - 1e-9);
    },
  },
  baldwin: {
    bars: bordaAlive,
    majority: false,
    roundKey: 'replay.elim.baldwinRound',
    doomed: (_r, alive, m, bars) => {
      let worst = -1;
      for (let i = 0; i < m; i++) if (alive[i] && (worst < 0 || bars[i] < bars[worst])) worst = i;
      return worst >= 0 ? [worst] : [];
    },
  },
};

function traceElimGeneric(
  cands: NamedPt[],
  ranks: number[][],
  m: number,
  spec: ElimSpec
): TraceFrame[] {
  const alive = new Array(m).fill(true);
  let remaining = m;
  let round = 1;
  const frames: TraceFrame[] = [];
  while (remaining > 1) {
    const bars = spec.bars(ranks, alive, m);
    const elimMask = alive.map((a) => !a);
    if (spec.majority) {
      const w = fpMajority(bars, alive);
      if (w >= 0) {
        frames.push({
          caption: { key: 'replay.elim.majority', params: { round, cand: cands[w].name } },
          bars,
          eliminated: elimMask,
          highlight: [w],
        });
        return frames;
      }
    }
    const doomed = spec.doomed(ranks, alive, m, bars);
    frames.push({
      caption: {
        key: spec.roundKey,
        params: { round, cand: doomed.map((i) => cands[i].name).join(', ') },
      },
      bars,
      eliminated: elimMask,
      highlight: doomed,
    });
    if (doomed.length === 0 || doomed.length >= remaining) break;
    for (const i of doomed) {
      alive[i] = false;
      remaining--;
    }
    round++;
  }
  const w = alive.findIndex((a) => a);
  frames.push({
    caption: { key: 'replay.elim.done', params: { cand: w >= 0 ? cands[w].name : '—' } },
    bars: spec.bars(ranks, alive, m),
    eliminated: alive.map((a) => !a),
    highlight: w >= 0 ? [w] : [],
  });
  return frames;
}

function traceTwoRound(cands: NamedPt[], ranks: number[][], m: number): TraceFrame[] {
  const allAlive = new Array(m).fill(true);
  const counts = firstPrefs(ranks, allAlive, m);
  const total = ranks.length;
  const frames: TraceFrame[] = [{ caption: { key: 'replay.elim.tr1' }, bars: counts.slice() }];
  const leader = argmax(counts);
  if (counts[leader] > total / 2) {
    frames.push({
      caption: { key: 'replay.elim.majority', params: { round: 1, cand: cands[leader].name } },
      bars: counts.slice(),
      highlight: [leader],
    });
    return frames;
  }
  const order = counts.map((_, i) => i).sort((a, b) => counts[b] - counts[a]);
  const [a, b] = [order[0], order[1]];
  const alive = new Array(m).fill(false);
  alive[a] = true;
  alive[b] = true;
  const runoff = firstPrefs(ranks, alive, m);
  const elim = alive.map((x) => !x);
  frames.push({
    caption: { key: 'replay.elim.trRunoff', params: { a: cands[a].name, b: cands[b].name } },
    bars: runoff.slice(),
    eliminated: elim,
    highlight: [a, b],
  });
  const w = runoff[a] >= runoff[b] ? a : b;
  frames.push({
    caption: { key: 'replay.elim.done', params: { cand: cands[w].name } },
    bars: runoff.slice(),
    eliminated: elim,
    highlight: [w],
  });
  return frames;
}

function traceBucklin(cands: NamedPt[], ranks: number[][], m: number): TraceFrame[] {
  const n = ranks.length;
  const tally = new Array(m).fill(0);
  const frames: TraceFrame[] = [];
  for (let k = 0; k < m; k++) {
    for (const r of ranks) tally[r[k]] += 1;
    let best = -1;
    for (let i = 0; i < m; i++)
      if (tally[i] > n / 2 && (best < 0 || tally[i] > tally[best])) best = i;
    if (best >= 0) {
      frames.push({
        caption: {
          key: 'replay.elim.bucklinMajority',
          params: { round: k + 1, cand: cands[best].name },
        },
        bars: tally.slice(),
        highlight: [best],
      });
      return frames;
    }
    frames.push({
      caption: { key: 'replay.elim.bucklinRound', params: { round: k + 1 } },
      bars: tally.slice(),
    });
  }
  const w = argmax(tally);
  frames.push({
    caption: { key: 'replay.elim.done', params: { cand: cands[w].name } },
    bars: tally.slice(),
    highlight: [w],
  });
  return frames;
}

// Smith-IRV (Tideman): alternate "restrict to the Smith set" and "IRV-eliminate
// the plurality loser" until one remains. bars = first preferences among alive.
function traceSmithIRV(cands: NamedPt[], ranks: number[][], m: number): TraceFrame[] {
  const frames: TraceFrame[] = [];
  const alive = new Array(m).fill(true);
  let remaining = m;
  let round = 1;
  while (remaining > 1) {
    const S = smithSet(ranks, m, alive);
    const inS = new Set(S);
    if (S.length < remaining) {
      // Restriction beat: show the Smith set, mark the rest for elimination.
      frames.push({
        caption: {
          key: 'replay.smith.set',
          params: { cand: S.map((i) => cands[i].name).join(', ') },
        },
        bars: firstPrefs(ranks, alive, m),
        eliminated: alive.map((a) => !a),
        highlight: S,
      });
      for (let i = 0; i < m; i++)
        if (alive[i] && !inS.has(i)) {
          alive[i] = false;
          remaining -= 1;
        }
      if (remaining <= 1) break;
    }
    if (S.length === 1) break;
    // IRV beat among the Smith set.
    const fp = firstPrefs(ranks, alive, m);
    let min = Infinity;
    for (let i = 0; i < m; i++) if (alive[i] && fp[i] < min) min = fp[i];
    const doomed: number[] = [];
    for (let i = 0; i < m; i++) if (alive[i] && fp[i] === min) doomed.push(i);
    frames.push({
      caption: {
        key: 'replay.smith.irv',
        params: { round, cand: doomed.map((i) => cands[i].name).join(', ') },
      },
      bars: fp,
      eliminated: alive.map((a) => !a),
      highlight: doomed,
    });
    if (doomed.length >= remaining) break;
    for (const i of doomed) {
      alive[i] = false;
      remaining -= 1;
    }
    round += 1;
  }
  const w = alive.findIndex((a) => a);
  frames.push({
    caption: { key: 'replay.elim.done', params: { cand: w >= 0 ? cands[w].name : '—' } },
    bars: firstPrefs(ranks, alive, m),
    eliminated: alive.map((a) => !a),
    highlight: w >= 0 ? [w] : [],
  });
  return frames;
}

// Benham (Condorcet-IRV): each round, elect the Condorcet winner among the
// remaining candidates if there is one; otherwise IRV-eliminate the plurality loser.
function traceBenham(cands: NamedPt[], ranks: number[][], m: number): TraceFrame[] {
  const frames: TraceFrame[] = [];
  const alive = new Array(m).fill(true);
  let remaining = m;
  let round = 1;
  while (remaining > 1) {
    const cw = condorcetWinnerIdx(ranks, m, alive);
    const fp = firstPrefs(ranks, alive, m);
    if (cw >= 0) {
      frames.push({
        caption: { key: 'replay.benham.cw', params: { round, cand: cands[cw].name } },
        bars: fp,
        eliminated: alive.map((a) => !a),
        highlight: [cw],
      });
      return frames;
    }
    let min = Infinity;
    for (let i = 0; i < m; i++) if (alive[i] && fp[i] < min) min = fp[i];
    const doomed: number[] = [];
    for (let i = 0; i < m; i++) if (alive[i] && fp[i] === min) doomed.push(i);
    frames.push({
      caption: {
        key: 'replay.benham.round',
        params: { round, cand: doomed.map((i) => cands[i].name).join(', ') },
      },
      bars: fp,
      eliminated: alive.map((a) => !a),
      highlight: doomed,
    });
    if (doomed.length >= remaining) break;
    for (const i of doomed) {
      alive[i] = false;
      remaining -= 1;
    }
    round += 1;
  }
  const w = alive.findIndex((a) => a);
  frames.push({
    caption: { key: 'replay.elim.done', params: { cand: w >= 0 ? cands[w].name : '—' } },
    bars: firstPrefs(ranks, alive, m),
    eliminated: alive.map((a) => !a),
    highlight: w >= 0 ? [w] : [],
  });
  return frames;
}

/** Pairwise tally: beats[i][j] = voters ranking i above j. */
function pairwiseMatrix(ranks: number[][], m: number): number[][] {
  const b = Array.from({ length: m }, () => new Array(m).fill(0));
  for (const r of ranks) {
    const pos = new Array(m).fill(0);
    r.forEach((c, rank) => (pos[c] = rank));
    for (let i = 0; i < m; i++)
      for (let j = i + 1; j < m; j++) {
        if (pos[i] < pos[j]) b[i][j] += 1;
        else b[j][i] += 1;
      }
  }
  return b;
}

// Raynaud: each round, eliminate the loser of the single heaviest pairwise defeat.
// bars = duels won among the survivors (context for who's strong).
function traceRaynaud(cands: NamedPt[], ranks: number[][], m: number): TraceFrame[] {
  const b = pairwiseMatrix(ranks, m);
  const alive = new Array(m).fill(true);
  const wins = (): number[] => {
    const w = new Array(m).fill(0);
    for (let i = 0; i < m; i++)
      if (alive[i])
        for (let j = 0; j < m; j++) if (j !== i && alive[j] && b[i][j] > b[j][i]) w[i] += 1;
    return w;
  };
  const frames: TraceFrame[] = [];
  let remaining = m;
  let round = 1;
  while (remaining > 1) {
    let worst = -Infinity;
    let loser = -1;
    let beater = -1;
    for (let i = 0; i < m; i++)
      for (let j = 0; j < m; j++)
        if (i !== j && alive[i] && alive[j] && b[i][j] - b[j][i] > worst) {
          worst = b[i][j] - b[j][i];
          loser = j;
          beater = i;
        }
    if (loser < 0) break;
    frames.push({
      caption: {
        key: 'replay.raynaud.round',
        params: {
          round,
          a: cands[beater].name,
          b: cands[loser].name,
          av: b[beater][loser],
          bv: b[loser][beater],
        },
      },
      bars: wins(),
      eliminated: alive.map((a) => !a),
      highlight: [loser],
    });
    alive[loser] = false;
    remaining -= 1;
    round += 1;
  }
  const w = alive.findIndex((a) => a);
  frames.push({
    caption: { key: 'replay.elim.done', params: { cand: w >= 0 ? cands[w].name : '—' } },
    bars: wins(),
    eliminated: alive.map((a) => !a),
    highlight: w >= 0 ? [w] : [],
  });
  return frames;
}

// ── pairwise ──────────────────────────────────────────────────────────────────
// ponytail: bars show running Copeland (duels won) for ALL Condorcet methods —
// the shared intuition "who beats whom". Minimax/Schulze/Ranked-Pairs can crown a
// different winner than the Copeland leader on cyclic fields; the authoritative
// winner (from the engine) is what the final frame names, with a per-method note.
function tracePairwise(cands: NamedPt[], ranks: number[][], m: number, rule: Rule): TraceFrame[] {
  const wins = new Array(m).fill(0);
  const frames: TraceFrame[] = [{ caption: { key: 'replay.pairwise.start' }, bars: wins.slice() }];
  for (let i = 0; i < m; i++)
    for (let j = i + 1; j < m; j++) {
      let av = 0;
      let bv = 0;
      for (const r of ranks) {
        if (r.indexOf(i) < r.indexOf(j)) av++;
        else bv++;
      }
      const w = av >= bv ? i : j;
      wins[w] += 1;
      frames.push({
        caption: {
          key: 'replay.pairwise.duel',
          params: { a: cands[i].name, b: cands[j].name, av, bv, cand: cands[w].name },
        },
        bars: wins.slice(),
        highlight: [i, j],
      });
    }
  const winner = ruleWinnerFromRanks(ranks, m, rule);
  const doneKey =
    rule === 'minimax'
      ? 'replay.pairwise.doneMinimax'
      : rule === 'schulze'
        ? 'replay.pairwise.doneSchulze'
        : rule === 'ranked_pairs'
          ? 'replay.pairwise.doneRankedPairs'
          : rule === 'black'
            ? 'replay.pairwise.doneBlack'
            : rule === 'split_cycle'
              ? 'replay.pairwise.doneSplitCycle'
              : rule === 'kemeny'
                ? 'replay.pairwise.doneKemeny'
                : rule === 'river'
                  ? 'replay.pairwise.doneRiver'
                  : 'replay.pairwise.doneCopeland';
  frames.push({
    caption: { key: doneKey, params: { cand: winner >= 0 ? cands[winner].name : '—' } },
    bars: wins.slice(),
    highlight: winner >= 0 ? [winner] : [],
  });
  return frames;
}

// ── twophase ──────────────────────────────────────────────────────────────────
function traceStar(cands: NamedPt[], scores: number[][], m: number): TraceFrame[] {
  const totals = new Array(m).fill(0);
  for (const s of scores) for (let i = 0; i < m; i++) totals[i] += s[i];
  const frames: TraceFrame[] = [
    { caption: { key: 'replay.phase.starScores' }, bars: totals.slice() },
  ];
  const order = totals.map((_, i) => i).sort((a, b) => totals[b] - totals[a]);
  const [a, b] = [order[0], order[1]];
  let av = 0;
  let bv = 0;
  for (const s of scores) {
    if (s[a] > s[b]) av++;
    else if (s[b] > s[a]) bv++;
  }
  const rbars = new Array(m).fill(0);
  rbars[a] = av;
  rbars[b] = bv;
  const elim = new Array(m).fill(true);
  elim[a] = false;
  elim[b] = false;
  frames.push({
    caption: { key: 'replay.phase.starRunoff', params: { a: cands[a].name, b: cands[b].name } },
    bars: rbars.slice(),
    eliminated: elim.slice(),
    highlight: [a, b],
  });
  const w = av >= bv ? a : b;
  frames.push({
    caption: { key: 'replay.phase.done', params: { cand: cands[w].name } },
    bars: rbars.slice(),
    eliminated: elim.slice(),
    highlight: [w],
  });
  return frames;
}

function traceMJ(cands: NamedPt[], ranks: number[][], scores: number[][], m: number): TraceFrame[] {
  const L = 6;
  const grades = cands.map((_, i) => {
    const g = scores.map((s) => Math.round(s[i] * (L - 1))).sort((x, y) => x - y);
    return g.length ? g[Math.floor((g.length - 1) / 2)] : 0;
  });
  const frames: TraceFrame[] = [
    { caption: { key: 'replay.phase.mjMedian' }, bars: grades.slice() },
  ];
  const winner = ruleWinnerFromRanks(ranks, m, 'majority_judgment', scores);
  frames.push({
    caption: { key: 'replay.phase.done', params: { cand: winner >= 0 ? cands[winner].name : '—' } },
    bars: grades.slice(),
    highlight: winner >= 0 ? [winner] : [],
  });
  return frames;
}

// ── lottery ─────────────────────────────────────────────────────────────────
function traceLottery(cands: NamedPt[], ranks: number[][], m: number): TraceFrame[] {
  const counts = firstPrefs(ranks, new Array(m).fill(true), m);
  const w = argmax(counts);
  return [
    { caption: { key: 'replay.lottery.shares' }, bars: counts.slice() },
    {
      caption: { key: 'replay.lottery.draw', params: { cand: cands[w].name } },
      bars: counts.slice(),
      highlight: [w],
    },
  ];
}

// ── Public entry ──────────────────────────────────────────────────────────────
/** Build the replay of `rule` over an already-sampled set of spatial voters. */
export function buildTrace(sample: Pt[], cands: NamedPt[], rule: Rule): VoteTrace {
  const ranks = computeRanks(sample, cands);
  const scores = computeScores(sample, cands);
  return buildTraceFromBallots(cands, ranks, scores, rule, sample.length);
}

/**
 * Build the replay of `rule` over ballots that already exist as ranks + scores —
 * e.g. language-transformed ballots (a single-name ballot keeps only its top
 * choice), so the dépouillement counts what was really cast, not full preferences.
 * The authoritative winner still comes from the engine over these same ballots.
 */
export function buildTraceFromBallots(
  cands: NamedPt[],
  ranks: number[][],
  scores: number[][],
  rule: Rule,
  sampleSize = ranks.length
): VoteTrace {
  const m = cands.length;
  const family = FAMILY_OF[rule];
  const winner = ruleWinnerFromRanks(ranks, m, rule, CARDINAL_RULES.has(rule) ? scores : undefined);

  let frames: TraceFrame[];
  if (family === 'count') frames = traceCount(cands, ranks, scores, rule, m);
  else if (family === 'pairwise') frames = tracePairwise(cands, ranks, m, rule);
  else if (family === 'lottery') frames = traceLottery(cands, ranks, m);
  else if (family === 'twophase')
    frames = rule === 'star' ? traceStar(cands, scores, m) : traceMJ(cands, ranks, scores, m);
  else if (rule === 'two_round') frames = traceTwoRound(cands, ranks, m);
  else if (rule === 'bucklin') frames = traceBucklin(cands, ranks, m);
  else if (rule === 'smith_irv') frames = traceSmithIRV(cands, ranks, m);
  else if (rule === 'benham') frames = traceBenham(cands, ranks, m);
  else if (rule === 'raynaud') frames = traceRaynaud(cands, ranks, m);
  else frames = traceElimGeneric(cands, ranks, m, ELIM_SPECS[rule]!);

  // The engine has the final say on the winner; make the last beat agree with it
  // (a rare exact tie ⇒ winner < 0 ⇒ a "no decisive winner" frame).
  const last = frames[frames.length - 1];
  frames[frames.length - 1] =
    winner < 0
      ? { ...last, caption: { key: 'replay.tie' }, highlight: [] }
      : { ...last, highlight: [winner] };

  return { family, rule, frames, winner, unitKey: UNIT_OF[rule], sampleSize };
}
