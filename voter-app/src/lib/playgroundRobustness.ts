import { ruleWinner, type NamedPt, type Pt, type Rule } from './playgroundVoting';

// Robustness of the field winner. The instrument shows the winner on ONE drawn
// electorate; this re-draws the SAME composition on `draws` other seeds and
// tallies who wins under the rule each time. The honest read of "the method
// decides" is a frequency — "Bob wins in 78% of resamples" — not a single point.

export interface WinnerShare {
  name: string;
  count: number;
  share: number; // 0..1
}

export interface WinnerDistribution {
  shares: WinnerShare[]; // sorted desc by count
  total: number; // resamples that produced a winner
  modal: string | null; // most frequent winner
  modalShare: number; // 0..1
}

// Knuth multiplicative hash → well-spread, decorrelated seeds from a base.
const seedAt = (base: number, i: number): number => (base + 1 + i * 2654435761) >>> 0;

export function winnerDistribution(
  sampleAtSeed: (seed: number) => Pt[],
  candidates: NamedPt[],
  rule: Rule,
  draws: number,
  baseSeed: number
): WinnerDistribution {
  const tally = new Map<string, number>();
  let total = 0;
  for (let i = 0; i < draws; i++) {
    const idx = ruleWinner(sampleAtSeed(seedAt(baseSeed, i)), candidates, rule);
    if (idx < 0) continue;
    const name = candidates[idx].name;
    tally.set(name, (tally.get(name) ?? 0) + 1);
    total++;
  }
  const shares: WinnerShare[] = [...tally.entries()]
    .map(([name, count]) => ({ name, count, share: total ? count / total : 0 }))
    .sort((a, b) => b.count - a.count);
  return {
    shares,
    total,
    modal: shares[0]?.name ?? null,
    modalShare: shares[0]?.share ?? 0,
  };
}
