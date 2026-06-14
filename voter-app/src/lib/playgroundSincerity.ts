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
      verdicts.push({ rule, sincereWinner: '—', sincereIsBest: true, temptation: null });
      continue;
    }
    let temptation: SincerityVerdict['temptation'] = null;

    // ── Compromise ("vote utile"): rank a candidate you prefer to w0 first,
    //    burying w0 last. Try your most-preferred such candidate first. ──
    const better = ranking.filter((c) => c !== w0 && util[c] > util[w0] + EPS);
    for (const c of better) {
      const stratRank = [c, ...sincereRow.filter((x) => x !== c && x !== w0), w0];
      const stratScore = cands.map((_, i) => (i === c ? 1 : 0)); // bullet-vote c
      const w1 = winnerWith(rule, stratRank, stratScore);
      if (util[w1] > util[w0] + EPS) {
        temptation = { type: 'compromise', voteFor: cands[c].name, newWinner: cands[w1].name };
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
      }
    }

    verdicts.push({
      rule,
      sincereWinner: cands[w0].name,
      sincereIsBest: temptation === null,
      temptation,
    });
  }

  return { ranking: rankingNames, blocSize, verdicts };
}
