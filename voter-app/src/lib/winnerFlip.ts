// winnerFlip — "the winner just changed from A to B": the pure bookkeeping behind the winner
// strip's flip sentence. A flip is a change of winner under the SAME method and the SAME field
// of candidates (a drag, a shake, a slider); switching the method or editing the candidates is
// a different question, not a flip, so it starts over.

export interface WinnerMark {
  /** The method the winner is read under. */
  rule: string;
  /** The candidates' names, in order: an edit of the field (add, remove, rename) is not a flip. */
  names: readonly string[];
  /** The displayed winner's name. */
  winner: string;
}

export interface Flip {
  from: string;
  to: string;
}

const sameNames = (a: readonly string[], b: readonly string[]): boolean =>
  a.length === b.length && a.every((n, i) => n === b[i]);

/**
 * The flip to show after the winner is read as `now`, having been read as `prev` with `flip`
 * showing. The latest change wins (A → B → C reads "B → C"); a return to where the flip began
 * (A → B → A) is no change at all.
 */
export function nextFlip(
  prev: WinnerMark | null,
  now: WinnerMark | null,
  flip: Flip | null
): Flip | null {
  if (prev === null || now === null) return null;
  if (prev.rule !== now.rule || !sameNames(prev.names, now.names)) return null;
  if (prev.winner === now.winner) return flip;
  if (flip !== null && flip.from === now.winner) return null;
  return { from: prev.winner, to: now.winner };
}
