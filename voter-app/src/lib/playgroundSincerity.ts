// playgroundSincerity.ts — the project's central question made interactive:
// does a voting method let you vote by CONVICTION, or does it tempt you to vote
// "utile" (strategically)?
//
// You are a voter with sincere spatial preferences. Your single voice is rarely
// pivotal in a large electorate — so strategic pressure is modelled as a *bloc*
// of voters who share your conviction (a stated, honest framing: the temptation
// to betray your favourite is collective). For each rule we test whether your
// bloc's sincere ballot is its best response, or whether a canonical strategic
// deviation elects a candidate you prefer:
//   · compromise ("vote utile") — rank a more viable candidate you prefer first,
//     burying the sincere winner;
//   · burying — keep your favourite first but push the sincere winner last.
// Pure + deterministic; reuses the playground voting lib (no smuggled model).

import {
  computeRanks,
  computeScores,
  ruleWinnerFromRanks,
  CARDINAL_RULES,
  type NamedPt,
  type Pt,
  type Rule,
} from './playgroundVoting';
import { LEADER_RULES } from './scorecard';

export interface SincerityVerdict {
  rule: Rule;
  /** Candidate name elected when your bloc votes sincerely. */
  sincereWinner: string;
  /** True = sincere voting is your best response (conviction rewarded). */
  sincereIsBest: boolean;
  /** How much closer (proximity gained) the lie's winner is to you vs the sincere
   *  winner — the size of the betrayal incentive. 0 when sincere is best. */
  gain: number;
  /** The cheapest beneficial lie, when one exists. */
  temptation: {
    type: 'compromise' | 'burying';
    /** The candidate your bloc would insincerely rank first. */
    voteFor: string;
    /** Who wins once your bloc lies — a candidate you prefer to the sincere winner. */
    newWinner: string;
  } | null;
}

export interface SincerityReport {
  /** Your sincere ranking of the candidates, best → worst (names). */
  ranking: string[];
  /** Number of voters in your conviction bloc. */
  blocSize: number;
  verdicts: SincerityVerdict[];
}

const EPS = 1e-9;

function dist(a: Pt, b: NamedPt): number {
  const dz = (a.z ?? 0) - (b.z ?? 0);
  return Math.hypot(a.x - b.x, a.y - b.y, dz);
}

/**
 * Probe, rule by rule, whether your conviction bloc is tempted to vote
 * strategically. `blocShare` ∈ [0,1] sizes your bloc relative to the rest of the
 * electorate (`others`, who vote sincerely). Returns one verdict per leader rule.
 */
export function sincerityProbe(
  youPos: Pt,
  blocShare: number,
  others: Pt[],
  cands: NamedPt[]
): SincerityReport {
  const m = cands.length;
  const util = cands.map((c) => -dist(youPos, c)); // higher = closer = better for you
  const ranking = cands.map((_, i) => i).sort((a, b) => util[b] - util[a]);
  const rankingNames = ranking.map((i) => cands[i].name);

  const blocSize = Math.max(1, Math.round(Math.max(0, Math.min(1, blocShare)) * others.length));
  // Your bloc = identical copies of you, appended after the sincere electorate.
  const electorate: Pt[] = others.concat(Array.from({ length: blocSize }, () => youPos));
  const blocStart = others.length;

  const verdicts: SincerityVerdict[] = [];
  if (m < 3) {
    // No strategic dilemma exists with fewer than three candidates.
    for (const rule of LEADER_RULES) {
      const ranks = computeRanks(electorate, cands);
      const scores = computeScores(electorate, cands);
      const w = ruleWinnerFromRanks(ranks, m, rule, scores);
      verdicts.push({
        rule,
        sincereWinner: w >= 0 ? cands[w].name : '—',
        sincereIsBest: true,
        gain: 0,
        temptation: null,
      });
    }
    return { ranking: rankingNames, blocSize, verdicts };
  }

  const baseRanks = computeRanks(electorate, cands);
  const baseScores = computeScores(electorate, cands);
  const sincereRow = ranking; // the bloc's sincere ranking (indices best→worst)

  // Recompute the winner with the bloc rows overridden by a strategic ballot.
  const winnerWith = (rule: Rule, stratRank: number[], stratScore: number[] | null): number => {
    const ranks = baseRanks.map((r, v) => (v >= blocStart ? stratRank : r));
    const scores = CARDINAL_RULES.has(rule)
      ? baseScores.map((s, v) => (v >= blocStart && stratScore ? stratScore : s))
      : baseScores;
    return ruleWinnerFromRanks(ranks, m, rule, scores);
  };

  for (const rule of LEADER_RULES) {
    const w0 = ruleWinnerFromRanks(baseRanks, m, rule, baseScores);
    if (w0 < 0) {
      verdicts.push({ rule, sincereWinner: '—', sincereIsBest: true, gain: 0, temptation: null });
      continue;
    }
    // Random ballot is strategyproof (Gibbard, 1977): misrepresenting your top
    // choice only lowers your expected utility — conviction is always best.
    if (rule === 'random_ballot') {
      verdicts.push({
        rule,
        sincereWinner: cands[w0].name,
        sincereIsBest: true,
        gain: 0,
        temptation: null,
      });
      continue;
    }
    let temptation: SincerityVerdict['temptation'] = null;
    let gain = 0;

    // ── Compromise ("vote utile"): rank a candidate you prefer to w0 first,
    //    burying w0 last. Try your most-preferred such candidate first. ──
    const better = ranking.filter((c) => c !== w0 && util[c] > util[w0] + EPS);
    for (const c of better) {
      const stratRank = [c, ...sincereRow.filter((x) => x !== c && x !== w0), w0];
      const stratScore = cands.map((_, i) => (i === c ? 1 : 0)); // bullet-vote c
      const w1 = winnerWith(rule, stratRank, stratScore);
      if (util[w1] > util[w0] + EPS) {
        temptation = { type: 'compromise', voteFor: cands[c].name, newWinner: cands[w1].name };
        gain = util[w1] - util[w0];
        break;
      }
    }

    // ── Burying: keep your favourite first, push the sincere winner last. ──
    if (!temptation && ranking[0] !== w0) {
      const fav = ranking[0];
      const stratRank = [fav, ...sincereRow.filter((x) => x !== fav && x !== w0), w0];
      const stratScore = cands.map((_, i) => (i === w0 ? 0 : Math.max(0, util[i] - util[w0])));
      const w1 = winnerWith(rule, stratRank, stratScore);
      if (util[w1] > util[w0] + EPS) {
        temptation = { type: 'burying', voteFor: cands[fav].name, newWinner: cands[w1].name };
        gain = util[w1] - util[w0];
      }
    }

    verdicts.push({
      rule,
      sincereWinner: cands[w0].name,
      sincereIsBest: temptation === null,
      gain: Math.round(gain * 1000) / 1000,
      temptation,
    });
  }

  return { ranking: rankingNames, blocSize, verdicts };
}

export interface ScanRow {
  rule: Rule;
  /** Share of sampled voters whom the method tempts to vote strategically, [0,1]. */
  temptRate: number;
}

export interface SincerityScan {
  /** Number of voter archetypes sampled from the electorate. */
  sampled: number;
  /** One row per rule, sorted best-first (lowest temptation rate). */
  rows: ScanRow[];
}

/**
 * Sweep the electorate: take `sampleSize` real voters as sincere archetypes and,
 * for each method, measure how OFTEN a voter (with a conviction bloc of
 * `blocShare`) is tempted to vote strategically. The synthesis the project's goal
 * asks for — on THIS electorate, which methods best let voters keep their
 * conviction. A stated convention (the two canonical strategies), not a theorem.
 */
export function sincerityScan(
  others: Pt[],
  cands: NamedPt[],
  blocShare: number,
  sampleSize = 40
): SincerityScan {
  if (others.length === 0 || cands.length < 3) {
    return { sampled: 0, rows: LEADER_RULES.map((rule) => ({ rule, temptRate: 0 })) };
  }
  // Evenly-strided voter archetypes (deterministic).
  const step = Math.max(1, others.length / sampleSize);
  const picks: Pt[] = [];
  for (let i = 0; i < others.length && picks.length < sampleSize; i += step) {
    picks.push(others[Math.floor(i)]);
  }
  const tempted: Record<string, number> = {};
  for (const rule of LEADER_RULES) tempted[rule] = 0;
  for (const you of picks) {
    const { verdicts } = sincerityProbe(you, blocShare, others, cands);
    for (const v of verdicts) if (!v.sincereIsBest) tempted[v.rule] += 1;
  }
  const rows: ScanRow[] = LEADER_RULES.map((rule) => ({
    rule,
    temptRate: Math.round((tempted[rule] / picks.length) * 1000) / 1000,
  })).sort((a, b) => a.temptRate - b.temptRate);
  return { sampled: picks.length, rows };
}

export type ManipKind = 'compromise' | 'burying' | null;

interface VoterProbe {
  kind: ManipKind;
  /** The strategic ballot to cast when kind != null (else the sincere ranking). */
  rank: number[];
  /** Cardinal strategic score, or null for ordinal rules. */
  score: number[] | null;
}

// Probe ONE voter, treated as a conviction bloc of `blocSize`, against the sincere
// winner of (base electorate + that bloc). Returns the cheapest beneficial
// canonical lie's ballot, or { kind: null } when conviction is the best response.
// The single source of the strategic model — shared by the manipulation lens
// (which reads .kind) and strategicVote (which also casts .rank/.score).
function probeVoter(
  you: Pt,
  cands: NamedPt[],
  rule: Rule,
  m: number,
  baseRanks: number[][],
  baseScores: number[][] | undefined,
  blocSize: number,
  tactic: 'auto' | 'compromise' | 'burying' = 'auto'
): VoterProbe {
  const cardinal = baseScores !== undefined;
  const util = cands.map((c) => -dist(you, c));
  const ranking = cands.map((_, i) => i).sort((a, b) => util[b] - util[a]);
  const youScore = cardinal ? computeScores([you], cands)[0] : null;

  const sincereRanks = baseRanks.concat(Array.from({ length: blocSize }, () => ranking));
  const sincereScores =
    cardinal && youScore
      ? baseScores.concat(Array.from({ length: blocSize }, () => youScore))
      : undefined;
  const blocStart = baseRanks.length;
  const w0 = ruleWinnerFromRanks(sincereRanks, m, rule, sincereScores);
  if (w0 < 0) return { kind: null, rank: ranking, score: null };

  const winnerWith = (stratRank: number[], stratScore: number[] | null): number => {
    const ranks = sincereRanks.map((r, v) => (v >= blocStart ? stratRank : r));
    const scores =
      cardinal && sincereScores
        ? sincereScores.map((s, v) => (v >= blocStart && stratScore ? stratScore : s))
        : sincereScores;
    return ruleWinnerFromRanks(ranks, m, rule, scores);
  };

  // Compromise ("vote utile"): a preferred candidate first, w0 buried last.
  if (tactic === 'auto' || tactic === 'compromise') {
    const better = ranking.filter((c) => c !== w0 && util[c] > util[w0] + EPS);
    for (const c of better) {
      const rank = [c, ...ranking.filter((x) => x !== c && x !== w0), w0];
      const score = cands.map((_, i) => (i === c ? 1 : 0));
      if (util[winnerWith(rank, score)] > util[w0] + EPS)
        return { kind: 'compromise', rank, score: cardinal ? score : null };
    }
  }
  // Burying: keep the favourite first, push the sincere winner last.
  if ((tactic === 'auto' || tactic === 'burying') && ranking[0] !== w0) {
    const fav = ranking[0];
    const rank = [fav, ...ranking.filter((x) => x !== fav && x !== w0), w0];
    const score = cands.map((_, i) => (i === w0 ? 0 : Math.max(0, util[i] - util[w0])));
    if (util[winnerWith(rank, score)] > util[w0] + EPS)
      return { kind: 'burying', rank, score: cardinal ? score : null };
  }
  return { kind: null, rank: ranking, score: null };
}

/**
 * Per-voter strategic-temptation field under ONE rule — the spatial face of the
 * sincerity question, for the central-map "Manipulation" lens. Each voter is
 * treated as a conviction bloc (`blocShare` of the electorate, the rest sincere);
 * we report whether a canonical lie elects a candidate they prefer:
 *   · 'compromise' — rank a more viable preferred candidate first (vote utile);
 *   · 'burying'    — keep the favourite first but push the sincere winner last;
 *   · null         — sincere voting is the bloc's best response (conviction wins).
 * Random ballot is strategyproof (Gibbard 1977) → every voter is null. Pure +
 * deterministic; reuses the playground voting lib (same model as sincerityProbe).
 */
export function manipulationField(
  voters: Pt[],
  cands: NamedPt[],
  rule: Rule,
  blocShare: number,
  tactic: 'auto' | 'compromise' | 'burying' = 'auto'
): ManipKind[] {
  const m = cands.length;
  if (m < 3 || voters.length === 0 || rule === 'random_ballot') {
    return voters.map(() => null);
  }
  const cardinal = CARDINAL_RULES.has(rule);
  const baseRanks = computeRanks(voters, cands);
  const baseScores = cardinal ? computeScores(voters, cands) : undefined;
  const blocSize = Math.max(1, Math.round(Math.max(0, Math.min(1, blocShare)) * voters.length));
  return voters.map(
    (you) => probeVoter(you, cands, rule, m, baseRanks, baseScores, blocSize, tactic).kind
  );
}

export type Behavior = 'sincere' | 'strategic' | 'mixed';

/** Which insincere ballot a tempted bloc casts. The client (permutation) engine
 *  faithfully represents the two *reordering* tactics; truncation (later-no-harm)
 *  and abstention (no-show) need real partial ballots and live in the backend. */
export type Tactic = 'compromise' | 'burying';

export interface StrategicOutcome {
  /** Winner index when everyone votes their true preference. */
  sincereWinner: number;
  /** Winner index once tempted voters cast their strategic ballot. */
  strategicWinner: number;
  /** Per sampled voter: did they actually defect from sincere voting? */
  defectors: boolean[];
  /** Share of the sample that defected, [0,1]. */
  defectRate: number;
  sampled: number;
}

// A voter defects if their conviction bloc (this share of the electorate) would
// gain — same threshold as the manipulation lens, so colour and outcome agree.
const STRAT_BLOC_SHARE = 0.2;
// Cap the electorate for the O(n²) probe so it stays snappy on drag-settle.
const STRAT_CAP = 240;

/**
 * One-shot best response to sincere voting: every voter the method tempts casts
 * the canonical lie (compromise or burying), then the winner is recomputed once.
 * 'mixed' = every other tempted voter acts; 'sincere' = nobody (winner unchanged).
 * A stated behavioural convention (the same model as the manipulation lens), not
 * an equilibrium solver. Pure + deterministic.
 */
export function strategicVote(
  voters: Pt[],
  cands: NamedPt[],
  rule: Rule,
  behavior: Behavior,
  opts: { tactic?: Tactic | 'auto'; blocShare?: number } = {}
): StrategicOutcome | null {
  const { tactic = 'auto', blocShare = STRAT_BLOC_SHARE } = opts;
  const m = cands.length;
  if (m < 2 || voters.length === 0) return null;
  const step = Math.max(1, Math.ceil(voters.length / STRAT_CAP));
  const sample = voters.filter((_, i) => i % step === 0);
  const n = sample.length;
  const cardinal = CARDINAL_RULES.has(rule);
  const baseRanks = computeRanks(sample, cands);
  const baseScores = cardinal ? computeScores(sample, cands) : undefined;
  const sincereWinner = ruleWinnerFromRanks(baseRanks, m, rule, baseScores);

  const defectors = new Array<boolean>(n).fill(false);
  // No dilemma when sincere, strategyproof, decisive winner missing, or < 3 cands.
  if (behavior === 'sincere' || m < 3 || rule === 'random_ballot' || sincereWinner < 0)
    return { sincereWinner, strategicWinner: sincereWinner, defectors, defectRate: 0, sampled: n };

  const blocSize = Math.max(1, Math.round(Math.max(0.01, Math.min(1, blocShare)) * n));
  const stratRanks = baseRanks.map((r) => r.slice());
  const stratScores = baseScores ? baseScores.map((s) => s.slice()) : undefined;

  let tempted = 0;
  for (let v = 0; v < n; v++) {
    const probe = probeVoter(sample[v], cands, rule, m, baseRanks, baseScores, blocSize, tactic);
    if (probe.kind === null) continue;
    const order = tempted++;
    if (behavior === 'mixed' && order % 2 === 1) continue; // only half act
    defectors[v] = true;
    stratRanks[v] = probe.rank;
    if (stratScores && probe.score) stratScores[v] = probe.score;
  }
  const strategicWinner = ruleWinnerFromRanks(stratRanks, m, rule, stratScores);
  const acted = defectors.reduce((s, d) => s + (d ? 1 : 0), 0);
  return { sincereWinner, strategicWinner, defectors, defectRate: acted / n, sampled: n };
}
