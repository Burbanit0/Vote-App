// explainWinner — turns a finished VoteTrace into ONE plain sentence: not "who
// won" (the bars already show that) but WHY, in the language of the method that
// produced it. A count winner has the highest total; an elim winner survived the
// transfers; a Condorcet winner beats everyone in a duel (in a cycle, nobody does); a runoff winner took
// the second round; a lottery winner was drawn.
//
// Pure: it returns an i18n key + params (never a rendered string), so it stays
// trivially testable and the component owns fr/en. It reads only the trace's
// authoritative winner and its final frame — it never re-derives the winner.

import { condorcetWinnerIdx, pairwise, type NamedPt } from './playgroundVoting';
import type { VoteTrace } from './voteTrace';

export interface WinnerExplanation {
  /** i18n key under the `playground` namespace (explain.*). */
  key: string;
  params: Record<string, string | number>;
}

/** Round for display: real-election transfers can be fractional; ballots aren't. */
const r = (n: number): number => Math.round(n);

/** Highest-scoring candidate in `bars` other than `except`, or -1 if none. */
function runnerUpIn(bars: number[], except: number): number {
  let best = -1;
  for (let i = 0; i < bars.length; i++) {
    if (i === except) continue;
    if (best < 0 || bars[i] > bars[best]) best = i;
  }
  return best;
}

export function explainWinner(trace: VoteTrace, cands: NamedPt[]): WinnerExplanation {
  const w = trace.winner;
  const winner = cands[w]?.name ?? '';
  const final = trace.frames[trace.frames.length - 1];
  const bars = final?.bars ?? [];
  const ru = runnerUpIn(bars, w);
  const runnerUp = ru >= 0 ? (cands[ru]?.name ?? '') : '';
  const winnerVal = r(bars[w] ?? 0);
  const runnerUpVal = ru >= 0 ? r(bars[ru]) : 0;

  const base = { winner, runnerUp, winnerVal, runnerUpVal };
  const pct = (v: number | undefined) => Math.round((v ?? 0) * 100); // no runner-up: 0
  // A sentence with figures says the winner leads on them: only when the figures as
  // shown (rounded) put the winner strictly ahead. A tie the engine broke, or a lead
  // lost to rounding, gets only "the rule elects them".
  const withFigures = (
    key: string,
    params: Record<string, string | number>,
    shown: [number, number] = [winnerVal, runnerUpVal]
  ): WinnerExplanation =>
    ru < 0 || shown[0] > shown[1] ? { key, params } : { key: 'explain.byRule', params: { winner } };

  // Rules whose family sentence would be false: their own wording, from the engine's
  // definitions in playgroundVoting.ts. Their final bars are not a deciding total (only
  // the winner is left, or they hold grades or minima), so most carry no figures.
  switch (trace.rule) {
    case 'maximin':
      return withFigures(
        'explain.maximin',
        { ...base, winnerPct: pct(bars[w]), runnerUpPct: pct(bars[ru]) },
        [pct(bars[w]), pct(bars[ru])]
      );
    case 'nash':
      return withFigures(
        'explain.nash',
        { ...base, winnerPct: pct(bars[w]), runnerUpPct: pct(bars[ru]) },
        [pct(bars[w]), pct(bars[ru])]
      );
    case 'irv':
      return withFigures('explain.irv', base);
    case 'two_round':
      return withFigures('explain.twoRound', base);
    case 'majority_judgment':
    case 'bucklin':
    case 'coombs':
    case 'nanson':
    case 'baldwin':
    case 'raynaud':
    case 'benham':
    case 'smith_irv':
      return { key: `explain.rule.${trace.rule}`, params: { winner } };
  }

  switch (trace.family) {
    case 'count':
      return withFigures('explain.count', base);
    case 'elim':
      return { key: 'explain.byRule', params: { winner } };
    case 'pairwise': {
      // The final bars count duels won outright (a tied duel counts for nobody). "Wins
      // every duel" is true only of a winner with all of them; otherwise (a cycle, or a
      // tied duel) the sentence says only that it does not beat every rival.
      const duels = cands.length - 1;
      return winnerVal >= duels
        ? { key: 'explain.pairwise', params: { winner } }
        : { key: 'explain.pairwiseCycle', params: { winner, wins: winnerVal, duels } };
    }
    case 'twophase':
      return withFigures('explain.twophase', base);
    case 'lottery':
      return { key: 'explain.lottery', params: { winner } };
  }
}

/** The Condorcet winner of these ballots, if any: who beats every rival head to head. */
export function condorcetOf(
  ranks: number[][],
  cands: NamedPt[]
): { idx: number; name: string | null } {
  const idx = condorcetWinnerIdx(ranks, cands.length);
  return { idx, name: idx >= 0 ? cands[idx].name : null };
}

/** Two winners head to head on the same ballots: the duel's winner `x` first, its loser
 * `y`, and whether the loser is `a` (the first group's winner). Null on a tie. */
export function headToHead(
  ranks: number[][],
  m: number,
  a: number,
  b: number
): { x: number; y: number; xv: number; yv: number; loserIsA: boolean } | null {
  const beats = pairwise(ranks, m);
  const [av, bv] = [beats[a][b], beats[b][a]];
  if (av === bv) return null;
  return av > bv
    ? { x: a, y: b, xv: av, yv: bv, loserIsA: false }
    : { x: b, y: a, xv: bv, yv: av, loserIsA: true };
}
