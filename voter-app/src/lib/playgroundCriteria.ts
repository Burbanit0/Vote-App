// playgroundCriteria.ts — the axiomatic criteria matrix, computed EMPIRICALLY on
// the current electorate (the playground's ethos: measured, live, "drag to find a
// violation" — not a memorised theorem table). For every leader rule we report,
// for THIS profile, whether the elected winner honours each criterion.
//
// A cell is `null` when the criterion isn't triggered on this electorate (e.g. no
// Condorcet winner exists, or nobody is a majority favourite). Random ballot is a
// lottery, so its deterministic representative would mislead — it carries its
// known ex-post properties instead (see RANDOM_BALLOT_PROPS).

import {
  computeRanks,
  computeScores,
  ruleWinnerFromRanks,
  fieldWinnerName,
  ruleWinner,
  CARDINAL_RULES,
  type NamedPt,
  type Pt,
  type Rule,
} from './playgroundVoting';
import { LEADER_RULES, condorcetFromRanks } from './scorecard';

export type CriterionId =
  | 'condorcet'
  | 'majority'
  | 'majority_loser'
  | 'condorcet_loser'
  | 'monotonic'
  | 'reversal'
  | 'pareto'
  | 'iia';

export type CritResult = boolean | null; // null = criterion not triggered here

export interface CriterionMeta {
  id: CriterionId;
  short: string; // compact column header
  fr: { label: string; desc: string };
  en: { label: string; desc: string };
}

export const CRITERIA: CriterionMeta[] = [
  {
    id: 'condorcet',
    short: 'Cond.',
    fr: {
      label: 'Condorcet',
      desc: 'Élit le vainqueur qui bat tous les autres en duel, quand il existe.',
    },
    en: {
      label: 'Condorcet',
      desc: 'Elects the candidate who beats all others pairwise, when one exists.',
    },
  },
  {
    id: 'majority',
    short: 'Maj.',
    fr: { label: 'Majorité', desc: 'Un candidat premier choix d’une majorité doit gagner.' },
    en: { label: 'Majority', desc: 'A candidate who is the first choice of a majority must win.' },
  },
  {
    id: 'majority_loser',
    short: 'Maj⁻',
    fr: {
      label: 'Perdant majoritaire',
      desc: 'N’élit jamais le candidat classé dernier par une majorité.',
    },
    en: {
      label: 'Majority loser',
      desc: 'Never elects the candidate a majority ranks last.',
    },
  },
  {
    id: 'condorcet_loser',
    short: 'Cond⁻',
    fr: {
      label: 'Perdant de Condorcet',
      desc: 'N’élit jamais le candidat battu par tous les autres en duel.',
    },
    en: {
      label: 'Condorcet loser',
      desc: 'Never elects the candidate who loses every pairwise duel.',
    },
  },
  {
    id: 'monotonic',
    short: 'Mono.',
    fr: {
      label: 'Monotonie',
      desc: 'Soutenir davantage le vainqueur ne doit pas le faire perdre (testé localement).',
    },
    en: {
      label: 'Monotonicity',
      desc: 'Ranking the winner higher must not make it lose (tested locally).',
    },
  },
  {
    id: 'reversal',
    short: 'Rev.',
    fr: {
      label: 'Symétrie de réversion',
      desc: 'Inverser tous les bulletins ne doit pas réélire le même vainqueur.',
    },
    en: {
      label: 'Reversal symmetry',
      desc: 'Reversing every ballot must not re-elect the same winner.',
    },
  },
  {
    id: 'pareto',
    short: 'Pareto',
    fr: {
      label: 'Pareto',
      desc: 'N’élit pas un candidat que tous préfèrent à un autre, battu par celui-ci.',
    },
    en: {
      label: 'Pareto',
      desc: 'Does not elect a candidate unanimously beaten by another.',
    },
  },
  {
    id: 'iia',
    short: 'IIA',
    fr: {
      label: 'Indép. aux non-pertinents',
      desc: 'Retirer un perdant ne doit pas changer le vainqueur (testé par retrait).',
    },
    en: {
      label: 'Independence (IIA)',
      desc: 'Removing a losing candidate must not change the winner (tested by removal).',
    },
  },
];

// Random ballot is a lottery; its deterministic representative is misleading, so
// we state its known ex-post properties (Gibbard 1977). Reversal is not meaningful
// for a first-preference lottery → null.
const RANDOM_BALLOT_PROPS: Record<CriterionId, CritResult> = {
  condorcet: false,
  majority: false,
  majority_loser: false,
  condorcet_loser: false,
  monotonic: true,
  reversal: null,
  pareto: true,
  iia: true,
};

/** Local pairwise tally pw[i][j] = ballots ranking i above j. */
function pairwise(ranks: number[][], m: number): number[][] {
  const pw = Array.from({ length: m }, () => new Array(m).fill(0));
  for (const r of ranks) {
    const pos = new Array(m).fill(0);
    r.forEach((c, i) => {
      pos[c] = i;
    });
    for (let i = 0; i < m; i++)
      for (let j = i + 1; j < m; j++) {
        if (pos[i] < pos[j]) pw[i][j] += 1;
        else pw[j][i] += 1;
      }
  }
  return pw;
}

export interface CriteriaRow {
  rule: Rule;
  winner: string | null;
  results: Record<CriterionId, CritResult>;
}

/**
 * Empirical criteria matrix over the current electorate: one row per leader rule,
 * ✓/✗/– per criterion for the winner THIS profile produces. Pure + deterministic.
 */
export function criteriaMatrix(voters: Pt[], cands: NamedPt[]): CriteriaRow[] {
  const m = cands.length;
  const n = voters.length;
  if (m === 0 || n === 0) {
    return LEADER_RULES.map((rule) => ({
      rule,
      winner: null,
      results: emptyResults(),
    }));
  }

  const baseRanks = computeRanks(voters, cands);
  const baseScores = computeScores(voters, cands);
  const pw = pairwise(baseRanks, m);
  const cw = condorcetFromRanks(baseRanks, m);

  // Majority favourite (first for >50%) and majority loser (last for >50%).
  const firsts = new Array(m).fill(0);
  const lasts = new Array(m).fill(0);
  for (const r of baseRanks) {
    firsts[r[0]] += 1;
    lasts[r[r.length - 1]] += 1;
  }
  const majFav = firsts.findIndex((c) => c > n / 2);
  const majLoser = lasts.findIndex((c) => c > n / 2);

  // Condorcet loser: beaten by every other candidate pairwise.
  let cl = -1;
  for (let i = 0; i < m; i++) {
    let losesAll = true;
    for (let j = 0; j < m && losesAll; j++) {
      if (i === j) continue;
      if (!(pw[j][i] > pw[i][j])) losesAll = false;
    }
    if (losesAll) {
      cl = i;
      break;
    }
  }

  return LEADER_RULES.map((rule) => {
    if (rule === 'random_ballot') {
      const w = ruleWinner(voters, cands, rule);
      return { rule, winner: w >= 0 ? cands[w].name : null, results: { ...RANDOM_BALLOT_PROPS } };
    }
    const cardinal = CARDINAL_RULES.has(rule);
    const scores = cardinal ? baseScores : undefined;
    const w = ruleWinnerFromRanks(baseRanks, m, rule, scores);
    const results = emptyResults();
    if (w >= 0) {
      results.condorcet = cw >= 0 ? w === cw : null;
      results.majority = majFav >= 0 ? w === majFav : null;
      results.majority_loser = majLoser >= 0 ? w !== majLoser : null;
      results.condorcet_loser = cl >= 0 ? w !== cl : null;
      results.monotonic = checkMonotonic(baseRanks, baseScores, m, rule, w, cardinal);
      results.reversal = checkReversal(baseRanks, baseScores, m, rule, w, cardinal);
      results.pareto = checkPareto(baseRanks, m, w);
      results.iia = checkIIA(voters, cands, rule, w);
    }
    return { rule, winner: w >= 0 ? cands[w].name : null, results };
  });
}

function emptyResults(): Record<CriterionId, CritResult> {
  return {
    condorcet: null,
    majority: null,
    majority_loser: null,
    condorcet_loser: null,
    monotonic: null,
    reversal: null,
    pareto: null,
    iia: null,
  };
}

/** Promote the winner one rank in ballots where it isn't first; it should not lose. */
function checkMonotonic(
  baseRanks: number[][],
  baseScores: number[][],
  m: number,
  rule: Rule,
  w: number,
  cardinal: boolean
): CritResult {
  let promoted = false;
  const ranks = baseRanks.map((r) => {
    const pos = r.indexOf(w);
    if (pos <= 0) return r;
    promoted = true;
    const nr = r.slice();
    [nr[pos - 1], nr[pos]] = [nr[pos], nr[pos - 1]];
    return nr;
  });
  if (!promoted) return null; // winner already top everywhere — can't test
  const scores = cardinal
    ? baseScores.map((s) => {
        const ns = s.slice();
        ns[w] = Math.min(1, ns[w] + 0.1);
        return ns;
      })
    : undefined;
  return ruleWinnerFromRanks(ranks, m, rule, scores) === w;
}

/** Reverse every ballot; the same winner should not be re-elected. */
function checkReversal(
  baseRanks: number[][],
  baseScores: number[][],
  m: number,
  rule: Rule,
  w: number,
  cardinal: boolean
): CritResult {
  const ranks = baseRanks.map((r) => r.slice().reverse());
  const scores = cardinal ? baseScores.map((s) => s.map((x) => 1 - x)) : undefined;
  return ruleWinnerFromRanks(ranks, m, rule, scores) !== w;
}

/** The winner must not be unanimously beaten by another candidate. */
function checkPareto(baseRanks: number[][], m: number, w: number): CritResult {
  for (let d = 0; d < m; d++) {
    if (d === w) continue;
    let dominates = true;
    for (const r of baseRanks) {
      if (r.indexOf(d) > r.indexOf(w)) {
        dominates = false;
        break;
      }
    }
    if (dominates) return false;
  }
  return true;
}

/** Removing any single losing candidate must not change the winner. */
function checkIIA(voters: Pt[], cands: NamedPt[], rule: Rule, w: number): CritResult {
  const wName = cands[w].name;
  for (let l = 0; l < cands.length; l++) {
    if (l === w) continue;
    const sub = cands.filter((_, i) => i !== l);
    if (sub.length < 2) continue;
    if (fieldWinnerName(voters, sub, rule) !== wName) return false;
  }
  return true;
}
