// realElections.ts — the project's thesis on REAL ballots, not a spatial model.
//
// The spatial engine (playgroundVoting.ts) always produces complete rankings;
// real ballots are TRUNCATED — voters rank a few candidates and leave the rest
// blank — and occasionally tie some. So this is a small, separate, truncation-
// aware tabulator over weighted partial orders, fed by genuine ranked-ballot data
// (PrefLib). It exists to show that on one real ballot box, the method changes the
// winner: Burlington 2009 elects Wright (plurality), Kiss (IRV) or Montroll
// (Condorcet) depending only on the rule. Pure + deterministic.
//
// We tabulate only the methods that are unambiguous on truncated ballots
// (plurality, two-round, IRV, and the Condorcet family via the pairwise matrix).
// Borda/score-family rules need a points convention the ballots don't supply, so
// they're out of scope here on purpose — see the note in the UI.

export interface RealBallot {
  /** Number of voters who cast exactly this order. */
  n: number;
  /** Ranked groups best→worst; each group is a set of equally-ranked candidate
   *  indices. Candidates absent from every group are unranked (below all). */
  groups: number[][];
}

export interface RealElection {
  id: string;
  title: string;
  titleEn: string;
  source: string;
  candidates: string[];
  voters: number;
  ballots: RealBallot[];
}

export interface MethodResult {
  /** Stable key for i18n/labels. */
  method: 'plurality' | 'two_round' | 'irv' | 'condorcet' | 'minimax';
  winner: string;
  /** One-line, human-readable evidence (counts) for this method's result. */
  detail: string;
}

export interface Backtest {
  election: RealElection;
  results: MethodResult[];
  /** Distinct winners across the methods — the headline number for the thesis. */
  distinctWinners: number;
}

// Group index of `cand` in a ballot, or Infinity if the voter left it unranked.
function groupOf(b: RealBallot, cand: number): number {
  for (let g = 0; g < b.groups.length; g++) if (b.groups[g].includes(cand)) return g;
  return Infinity;
}

// pair[a][b] = voters ranking a strictly above b. Unranked sits below every
// ranked candidate; two candidates in the same group (or both unranked) express
// no preference and count for neither.
function pairwise(el: RealElection): number[][] {
  const m = el.candidates.length;
  const pair = Array.from({ length: m }, () => new Array(m).fill(0));
  for (const b of el.ballots) {
    for (let a = 0; a < m; a++) {
      const ga = groupOf(b, a);
      for (let c = 0; c < m; c++) {
        if (a === c) continue;
        if (ga < groupOf(b, c)) pair[a][c] += b.n;
      }
    }
  }
  return pair;
}

// Each ballot's vote among the still-alive candidates: the highest-ranked group
// that contains any alive candidate, split evenly if it ties several alive ones.
// Returns per-candidate (possibly fractional) tallies; the rest exhausted.
function tallyAlive(el: RealElection, alive: boolean[]): number[] {
  const counts = new Array(el.candidates.length).fill(0);
  for (const b of el.ballots) {
    for (const group of b.groups) {
      const live = group.filter((c) => alive[c]);
      if (live.length > 0) {
        for (const c of live) counts[c] += b.n / live.length;
        break; // highest group with an alive candidate decides this ballot
      }
    }
  }
  return counts;
}

const argmax = (a: number[], ok: (i: number) => boolean = () => true): number => {
  let best = -1;
  for (let i = 0; i < a.length; i++) if (ok(i) && (best < 0 || a[i] > a[best])) best = i;
  return best;
};

function plurality(el: RealElection): MethodResult {
  const c = tallyAlive(
    el,
    el.candidates.map(() => true)
  );
  const w = argmax(c);
  return {
    method: 'plurality',
    winner: el.candidates[w],
    detail: `${el.candidates[w]} ${Math.round(c[w])} · ${el.candidates[runnerUp(c, w)]} ${Math.round(c[runnerUp(c, w)])}`,
  };
}

function runnerUp(c: number[], winner: number): number {
  return argmax(c, (i) => i !== winner);
}

function twoRound(el: RealElection, pair: number[][]): MethodResult {
  const first = tallyAlive(
    el,
    el.candidates.map(() => true)
  );
  const a = argmax(first);
  const b = runnerUp(first, a);
  const w = pair[a][b] >= pair[b][a] ? a : b;
  const l = w === a ? b : a;
  return {
    method: 'two_round',
    winner: el.candidates[w],
    detail: `${el.candidates[w]} ${pair[w][l]} · ${el.candidates[l]} ${pair[l][w]}`,
  };
}

function irv(el: RealElection): MethodResult {
  const m = el.candidates.length;
  const alive = el.candidates.map(() => true);
  let counts = tallyAlive(el, alive);
  let aliveN = m;
  while (aliveN > 2) {
    // Eliminate the alive candidate with the fewest current votes.
    const loser = argmax(
      counts.map((v) => -v),
      (i) => alive[i]
    );
    alive[loser] = false;
    aliveN--;
    counts = tallyAlive(el, alive);
  }
  const a = argmax(counts, (i) => alive[i]);
  const b = argmax(counts, (i) => alive[i] && i !== a);
  return {
    method: 'irv',
    winner: el.candidates[a],
    detail: `${el.candidates[a]} ${Math.round(counts[a])} · ${el.candidates[b]} ${Math.round(counts[b])}`,
  };
}

// Copeland: most pairwise wins minus losses. Equals the Condorcet winner whenever
// one exists (every candidate it beats; none beats it).
function condorcet(el: RealElection, pair: number[][]): MethodResult {
  const m = el.candidates.length;
  const score = new Array(m).fill(0);
  for (let a = 0; a < m; a++)
    for (let b = 0; b < m; b++)
      if (a !== b) score[a] += pair[a][b] > pair[b][a] ? 1 : pair[a][b] < pair[b][a] ? -1 : 0;
  const w = argmax(score);
  // Pairwise wins out of m-1 possible duels (m-1 = beats everyone = Condorcet winner).
  let wins = 0;
  for (let b = 0; b < m; b++) if (b !== w && pair[w][b] > pair[b][w]) wins++;
  return {
    method: 'condorcet',
    winner: el.candidates[w],
    detail: `${wins}/${m - 1}`,
  };
}

// Minimax: the candidate whose worst pairwise defeat (by margin) is least bad.
function minimax(el: RealElection, pair: number[][]): MethodResult {
  const m = el.candidates.length;
  const worstDefeat = new Array(m).fill(-Infinity);
  for (let a = 0; a < m; a++)
    for (let b = 0; b < m; b++)
      if (a !== b) worstDefeat[a] = Math.max(worstDefeat[a], pair[b][a] - pair[a][b]);
  // Least worst-defeat wins → maximise the negated value.
  const w = argmax(worstDefeat.map((v) => -v));
  // Worst pairwise margin against the winner; ≤0 means no head-to-head loss.
  return {
    method: 'minimax',
    winner: el.candidates[w],
    detail: worstDefeat[w] <= 0 ? '0' : `−${worstDefeat[w]}`,
  };
}

/** Run every truncation-safe method on a real ballot box. */
export function backtest(el: RealElection): Backtest {
  const pair = pairwise(el);
  const results = [
    plurality(el),
    twoRound(el, pair),
    irv(el),
    condorcet(el, pair),
    minimax(el, pair),
  ];
  return {
    election: el,
    results,
    distinctWinners: new Set(results.map((r) => r.winner)).size,
  };
}

/** The pairwise count a beats b — exposed for the verification test. */
export function pairwiseMatrix(el: RealElection): number[][] {
  return pairwise(el);
}
