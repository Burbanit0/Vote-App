// explainWinner — turns a finished VoteTrace into ONE plain sentence: not "who
// won" (the bars already show that) but WHY, in the language of the method that
// produced it. A count winner has the highest total; an elim winner survived the
// transfers; a Condorcet winner beats everyone in a duel; a runoff winner took
// the second round; a lottery winner was drawn.
//
// Pure: it returns an i18n key + params (never a rendered string), so it stays
// trivially testable and the component owns fr/en. It reads only the trace's
// authoritative winner and its final frame — it never re-derives the winner.

import type { NamedPt } from './playgroundVoting';
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

  switch (trace.family) {
    case 'count':
      return { key: 'explain.count', params: base };
    case 'elim':
      return { key: 'explain.elim', params: base };
    case 'pairwise':
      return { key: 'explain.pairwise', params: { winner } };
    case 'twophase':
      return { key: 'explain.twophase', params: base };
    case 'lottery':
      return { key: 'explain.lottery', params: { winner } };
  }
}
