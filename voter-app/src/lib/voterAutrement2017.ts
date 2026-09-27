// voterAutrement2017.ts — France 2017 presidential, the "Voter Autrement"
// in-situ approval experiment (Baujard, Igersheim, Lebon et al.).
//
// Unlike the ranked ballot boxes in realElections.ts, this is NOT re-tabulable
// ballot data: it is the published AGGREGATE approval rate per candidate (the
// share of experiment ballots approving them, corrected for France), set beside
// the official first-round plurality shares of the SAME election. So there is
// nothing to run through backtest() — the point isn't "same ballots, other
// method", it's "same electorate, other ballot FORMAT". And the twist is that
// the top name doesn't move (Macron leads both) while the order underneath
// collapses: Le Pen falls 2nd → 5th, Mélenchon climbs 4th → 2nd, so approval
// would have sent Macron into the runoff against Mélenchon, not Le Pen.
//
// Sources — approval rates: rangevoting.org/France2017 summary of the Baujard
// et al. experiment (3 894 approval ballots across 5 municipalities; on average
// 2.48 candidates approved per ballot). Official first-round shares: Ministère
// de l'Intérieur (they sum to 100.00). Caveat carried into the UI: the sample is
// self-selected and extrapolated, and an approval rate (a voter may approve
// several candidates) is not a vote share — the two columns are orderings to
// compare, not totals to add.

export interface CandidateShare {
  name: string;
  /** Official first-round vote share, % (Ministère de l'Intérieur). */
  plurality: number;
  /** Share of experiment ballots approving this candidate, % (France-corrected). */
  approval: number;
}

export const VOTER_AUTREMENT_2017: {
  approvalBallots: number;
  candidates: CandidateShare[];
} = {
  approvalBallots: 3894,
  candidates: [
    { name: 'Macron', plurality: 24.01, approval: 46.1 },
    { name: 'Le Pen', plurality: 21.3, approval: 27.5 },
    { name: 'Fillon', plurality: 20.01, approval: 30.1 },
    { name: 'Mélenchon', plurality: 19.58, approval: 39.4 },
    { name: 'Hamon', plurality: 6.36, approval: 36.3 },
    { name: 'Dupont-Aignan', plurality: 4.7, approval: 21.1 },
    { name: 'Lassalle', plurality: 1.21, approval: 7.4 },
    { name: 'Poutou', plurality: 1.09, approval: 15.5 },
    { name: 'Asselineau', plurality: 0.92, approval: 6.1 },
    { name: 'Arthaud', plurality: 0.64, approval: 8.7 },
    { name: 'Cheminade', plurality: 0.18, approval: 3.6 },
  ],
};

export interface ApprovalRow extends CandidateShare {
  /** 1-based rank under approval (desc). */
  approvalRank: number;
  /** 1-based rank under the official first round (desc). */
  pluralityRank: number;
  /** pluralityRank − approvalRank; > 0 means the candidate climbs under approval. */
  delta: number;
}

const rankMap = (key: 'approval' | 'plurality'): Record<string, number> => {
  const order = [...VOTER_AUTREMENT_2017.candidates].sort((a, b) => b[key] - a[key]);
  return Object.fromEntries(order.map((c, i) => [c.name, i + 1]));
};

/** Rows sorted by approval (desc), each carrying its rank in both orderings. */
export function reordering(): ApprovalRow[] {
  const aRank = rankMap('approval');
  const pRank = rankMap('plurality');
  return [...VOTER_AUTREMENT_2017.candidates]
    .sort((a, b) => b.approval - a.approval)
    .map((c) => ({
      ...c,
      approvalRank: aRank[c.name],
      pluralityRank: pRank[c.name],
      delta: pRank[c.name] - aRank[c.name],
    }));
}
