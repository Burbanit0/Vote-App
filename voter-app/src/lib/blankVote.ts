// blankVote.ts — pure logic for the "blank vote wins, now what?" reflection.
//
// The app's thesis, applied to the blank ballot: the voters don't change, the
// COUNTING RULE does. Given a fixed result (candidate shares + a blank share),
// four regimes each decide a different fate for the same ballots. This module
// only computes what each regime mechanically does — it takes no side on which
// is right. The narrative framing lives in the component; the civic answer is
// left to the reader.
//
// Lenses (drawn from the real regimes in data/blankVoteRegimes.ts):
//   france_today — blanks counted & published but EXCLUDED from suffrages
//                  exprimés (loi 2014): loud politically, mute legally.
//   in_exprimes  — reform hypothesis: blanks enter the denominator, so the
//                  majority threshold (50% of exprimés) gets harder to clear.
//   competitive  — Uruguay: the blank behaves like a candidate; if it outpolls
//                  the front-runner, the field reopens (fresh election).
//   threshold    — Colombia: a blank share above 50% annuls the election.

export type BlankLens = 'france_today' | 'in_exprimes' | 'competitive' | 'threshold';

export type BlankOutcome =
  | 'elected' // a candidate is elected; the blank had no legal effect
  | 'no_majority' // once blanks count, the winner falls below 50% → no clear mandate
  | 'blank_wins' // the blank outpolls the top candidate → fresh election
  | 'annulled'; // the blank crosses the threshold → election annulled

export interface BlankVerdict {
  lens: BlankLens;
  outcome: BlankOutcome;
  /** Index into `shares` of the leading candidate, or null when the blank prevails. */
  winner: number | null;
  /** Leading candidate's share of the expressed votes under this lens (0..1). */
  winnerShareOfExprimes: number;
  /** Does this regime send everyone back to the ballot box? */
  redo: boolean;
}

export const BLANK_LENSES: BlankLens[] = [
  'france_today',
  'in_exprimes',
  'competitive',
  'threshold',
];

function argmax(xs: number[]): number | null {
  let bi: number | null = null;
  let bv = -Infinity;
  xs.forEach((v, i) => {
    if (v > bv) {
      bv = v;
      bi = i;
    }
  });
  return bi;
}

/**
 * @param shares candidate shares as fractions of ALL ballots (need not sum to 1)
 * @param blank  blank share as a fraction of ALL ballots
 * @param knownWinner override the plurality-leader-of-`shares` winner with one
 *   already decided by an actual counting rule (Borda/IRV/Condorcet…), so the
 *   verdict is "blank vs. what THIS rule elected", not "blank vs. first place" —
 *   the app's whole thesis applied to the blank question. Omit to fall back to
 *   the abstract mixer's own plurality-of-shares reading (unchanged behaviour).
 */
export function blankVerdict(
  shares: number[],
  blank: number,
  lens: BlankLens,
  knownWinner?: number | null
): BlankVerdict {
  const candTotal = shares.reduce((a, b) => a + b, 0);
  const w = knownWinner !== undefined ? knownWinner : argmax(shares);
  const top = w === null ? 0 : shares[w];

  switch (lens) {
    case 'france_today': {
      // Blanks excluded from the denominator: the result is exactly as if they
      // had stayed home — someone is always elected.
      const denom = candTotal || 1;
      return {
        lens,
        outcome: 'elected',
        winner: w,
        winnerShareOfExprimes: top / denom,
        redo: false,
      };
    }
    case 'in_exprimes': {
      // Blanks in the denominator: a large blank share can pull the winner below
      // the 50% majority mark.
      const denom = candTotal + blank || 1;
      const share = top / denom;
      const hasMajority = share >= 0.5;
      return {
        lens,
        outcome: hasMajority ? 'elected' : 'no_majority',
        winner: w,
        winnerShareOfExprimes: share,
        redo: !hasMajority,
      };
    }
    case 'competitive': {
      // The blank is a contender: beat the front-runner and the field reopens.
      const blankWins = blank > top;
      const denom = candTotal + blank || 1;
      return {
        lens,
        outcome: blankWins ? 'blank_wins' : 'elected',
        winner: blankWins ? null : w,
        winnerShareOfExprimes: blankWins ? blank / denom : top / (candTotal || 1),
        redo: blankWins,
      };
    }
    case 'threshold': {
      // A blank majority annuls the election outright.
      const annul = blank > 0.5;
      return {
        lens,
        outcome: annul ? 'annulled' : 'elected',
        winner: annul ? null : w,
        winnerShareOfExprimes: annul ? blank : top / (candTotal || 1),
        redo: annul,
      };
    }
  }
}

export function allBlankVerdicts(shares: number[], blank: number): BlankVerdict[] {
  return BLANK_LENSES.map((l) => blankVerdict(shares, blank, l));
}
