// playgroundVoting.ts — fast, pure, client-side voting over a SPATIAL electorate
// (Lab reshape P2). Powers the live single-office canvas: an approximate winner +
// the win/entry-region overlay that reflows during drag. The backend profile engine
// remains the source of truth for the precise scorecard on drag-release.
//
// Voter utility for a candidate is -distance (closer = better). Everything derives
// from that: rankings for ordinal rules, per-voter min-max scores for cardinal ones.

// Points carry an optional 3rd axis. 1-D uses x (y=z=0); 2-D uses x,y (z=0);
// 3-D uses all three. z is optional so every existing 2-D caller is unchanged.
export interface NamedPt {
  name: string;
  x: number;
  y: number;
  z?: number;
  /** Stokes valence (see Pt.valence): non-spatial quality bonus on a candidate. */
  valence?: number;
}
export interface Pt {
  x: number;
  y: number;
  z?: number;
  /** Stokes valence: a non-spatial quality bonus on a CANDIDATE that lifts its
   *  utility for every voter (utility = -distance + valence). Optional and 0 by
   *  default, so positional-only callers are unchanged. Ignored on voter points. */
  valence?: number;
}

export type Dims = 1 | 2 | 3;

export type Rule =
  | 'plurality'
  | 'two_round'
  | 'irv'
  | 'borda'
  | 'approval'
  | 'condorcet'
  | 'minimax'
  | 'schulze'
  | 'bucklin'
  | 'coombs'
  | 'nanson'
  | 'baldwin'
  | 'ranked_pairs'
  | 'kemeny'
  | 'black'
  | 'anti_plurality'
  | 'random_ballot'
  | 'star'
  | 'majority_judgment'
  | 'score'
  // ── Tier B: "explained, not compared" — client-only extras. Available in the
  // method gallery + replay animation, but excluded from the comparison surfaces
  // (Bilan table, map picker, scorecard). No backend twin, no parity fixture. ──
  | 'dowdall'
  | 'smith_irv'
  | 'split_cycle'
  | 'cumulative'
  | 'maximin'
  | 'benham'
  | 'river'
  | 'nash'
  | 'raynaud';

export const RULE_LABELS: Record<Rule, string> = {
  plurality: 'Pluralité (1 tour)',
  two_round: 'Deux tours',
  irv: 'Vote alternatif (IRV)',
  borda: 'Borda',
  approval: 'Approbation',
  condorcet: 'Condorcet (Copeland)',
  minimax: 'Condorcet (minimax)',
  schulze: 'Condorcet (Schulze)',
  bucklin: 'Bucklin',
  coombs: 'Coombs',
  nanson: 'Nanson',
  baldwin: 'Baldwin',
  ranked_pairs: 'Condorcet (paires ordonnées)',
  random_ballot: 'Vote au sort (loterie)',
  star: 'STAR',
  majority_judgment: 'Jugement majoritaire',
  score: 'Note (score)',
  anti_plurality: 'Anti-pluralité (véto)',
  dowdall: 'Dowdall (Nauru)',
  black: 'Black (Condorcet-Borda)',
  smith_irv: 'Smith-IRV (Tideman)',
  split_cycle: 'Split Cycle',
  kemeny: 'Kemeny-Young',
  cumulative: 'Vote cumulatif',
  maximin: 'Maximin (utilité)',
  benham: 'Benham (Condorcet-IRV)',
  river: 'River',
  nash: 'Nash (produit d’utilités)',
  raynaud: 'Raynaud',
};

/** Cardinal rules need the per-voter score matrix, not just rankings. */
export const CARDINAL_RULES: ReadonlySet<Rule> = new Set<Rule>([
  'approval',
  'star',
  'majority_judgment',
  'score',
  'cumulative',
  'maximin',
  'nash',
]);

const dist = (a: Pt, b: Pt): number => Math.hypot(a.x - b.x, a.y - b.y, (a.z ?? 0) - (b.z ?? 0));

// Voter utility for a candidate: closer is better, lifted by the candidate's
// valence. Higher utility = preferred. Valence defaults to 0 (positional model).
const utility = (v: Pt, c: Pt): number => -dist(v, c) + (c.valence ?? 0);

/** Per-voter candidate-index ranking, best→worst (highest utility first). */
export function computeRanks(voters: Pt[], cands: Pt[]): number[][] {
  return voters.map((v) => {
    const idx = cands.map((_, i) => i);
    idx.sort((a, b) => utility(v, cands[b]) - utility(v, cands[a]));
    return idx;
  });
}

const rankings = computeRanks;

function pluralityCounts(ranks: number[][], alive: boolean[], m: number): number[] {
  const counts = new Array(m).fill(0);
  for (const r of ranks) {
    const top = r.find((i) => alive[i]);
    if (top !== undefined) counts[top] += 1;
  }
  return counts;
}

function argmax(arr: number[]): number {
  let best = 0;
  for (let i = 1; i < arr.length; i++) if (arr[i] > arr[best]) best = i;
  return best;
}

// ── Rules → winning candidate index ──────────────────────────────────────────

function winPlurality(ranks: number[][], m: number): number {
  return argmax(pluralityCounts(ranks, new Array(m).fill(true), m));
}

function winTwoRound(ranks: number[][], m: number): number {
  const counts = pluralityCounts(ranks, new Array(m).fill(true), m);
  const total = ranks.length;
  const leader = argmax(counts);
  if (counts[leader] > total / 2) return leader;
  // top-2 runoff
  const order = counts.map((_, i) => i).sort((a, b) => counts[b] - counts[a]);
  const [a, b] = [order[0], order[1]];
  let av = 0;
  let bv = 0;
  for (const r of ranks) {
    for (const i of r) {
      if (i === a) {
        av++;
        break;
      }
      if (i === b) {
        bv++;
        break;
      }
    }
  }
  return av >= bv ? a : b;
}

function winIRV(ranks: number[][], m: number): number {
  const alive = new Array(m).fill(true);
  let remaining = m;
  while (remaining > 1) {
    const counts = pluralityCounts(ranks, alive, m);
    const total = counts.reduce((s, c) => s + c, 0);
    const leader = argmax(counts);
    if (counts[leader] > total / 2) return leader;
    // Eliminate ALL alive candidates tied for the fewest first-prefs (including
    // any with zero) — a neutral, candidate-order-independent tie-break that
    // matches the backend engine (see playgroundVoting.parity.test.ts).
    let min = Infinity;
    for (let i = 0; i < m; i++) if (alive[i] && counts[i] < min) min = counts[i];
    const doomed: number[] = [];
    for (let i = 0; i < m; i++) if (alive[i] && counts[i] === min) doomed.push(i);
    if (doomed.length >= remaining) return -1; // every survivor tied → no winner
    for (const i of doomed) {
      alive[i] = false;
      remaining--;
    }
  }
  return alive.findIndex((a) => a);
}

function winBorda(ranks: number[][], m: number): number {
  const scores = new Array(m).fill(0);
  for (const r of ranks) {
    r.forEach((cand, rank) => {
      scores[cand] += m - 1 - rank;
    });
  }
  return argmax(scores);
}

/** Cardinal score in [0,1] per voter via min-max of -distance. */
export function computeScores(voters: Pt[], cands: Pt[]): number[][] {
  return voters.map((v) => {
    const u = cands.map((c) => utility(v, c));
    const lo = Math.min(...u);
    const hi = Math.max(...u);
    const span = hi - lo || 1;
    return u.map((x) => (x - lo) / span);
  });
}

function winApproval(scores: number[][], m: number): number {
  const counts = new Array(m).fill(0);
  for (const s of scores) {
    for (let i = 0; i < m; i++) if (s[i] >= 0.5) counts[i] += 1;
  }
  return argmax(counts);
}

/** Pairwise tally: beats[i][j] = number of voters ranking i above j. */
function pairwise(ranks: number[][], m: number): number[][] {
  const beats = Array.from({ length: m }, () => new Array(m).fill(0));
  for (const r of ranks) {
    const pos = new Array(m).fill(0);
    r.forEach((cand, rank) => {
      pos[cand] = rank;
    });
    for (let i = 0; i < m; i++) {
      for (let j = i + 1; j < m; j++) {
        if (pos[i] < pos[j]) beats[i][j] += 1;
        else beats[j][i] += 1;
      }
    }
  }
  return beats;
}

function winCondorcet(ranks: number[][], m: number): number {
  // Copeland: pairwise wins − losses; ties broken by Borda.
  const beats = pairwise(ranks, m);
  const copeland = new Array(m).fill(0);
  for (let i = 0; i < m; i++) {
    for (let j = 0; j < m; j++) {
      if (i === j) continue;
      if (beats[i][j] > beats[j][i]) copeland[i] += 1;
      else if (beats[i][j] < beats[j][i]) copeland[i] -= 1;
    }
  }
  const best = Math.max(...copeland);
  const tied = copeland.map((c, i) => (c === best ? i : -1)).filter((i) => i >= 0);
  if (tied.length === 1) return tied[0];
  return winBorda(ranks, m); // tie-break
}

/** Minimax (margins): elect the candidate whose worst pairwise defeat is least. */
function winMinimax(ranks: number[][], m: number): number {
  const b = pairwise(ranks, m);
  let best = 0;
  let bestWorst = Infinity;
  for (let i = 0; i < m; i++) {
    let worst = -Infinity;
    for (let j = 0; j < m; j++) {
      if (i === j) continue;
      worst = Math.max(worst, b[j][i] - b[i][j]); // margin of defeat by j
    }
    if (worst < bestWorst) {
      bestWorst = worst;
      best = i;
    }
  }
  return best;
}

/** Schulze (beatpaths): strongest-path winner via Floyd–Warshall. */
function winSchulze(ranks: number[][], m: number): number {
  const b = pairwise(ranks, m);
  const p = Array.from({ length: m }, () => new Array(m).fill(0));
  for (let i = 0; i < m; i++)
    for (let j = 0; j < m; j++) if (i !== j) p[i][j] = b[i][j] > b[j][i] ? b[i][j] : 0;
  for (let i = 0; i < m; i++)
    for (let j = 0; j < m; j++)
      if (i !== j)
        for (let k = 0; k < m; k++)
          if (i !== k && j !== k) p[j][k] = Math.max(p[j][k], Math.min(p[j][i], p[i][k]));
  for (let i = 0; i < m; i++) {
    let wins = true;
    for (let j = 0; j < m; j++)
      if (i !== j && p[j][i] > p[i][j]) {
        wins = false;
        break;
      }
    if (wins) return i;
  }
  return winBorda(ranks, m); // rare cyclic tie
}

/** Bucklin: descend ranks until a candidate reaches a majority of mentions. */
function winBucklin(ranks: number[][], m: number): number {
  const n = ranks.length;
  const tally = new Array(m).fill(0);
  for (let k = 0; k < m; k++) {
    for (const r of ranks) tally[r[k]] += 1;
    let best = -1;
    for (let i = 0; i < m; i++)
      if (tally[i] > n / 2 && (best === -1 || tally[i] > tally[best])) best = i;
    if (best >= 0) return best;
  }
  return argmax(tally);
}

/** Coombs: IRV but eliminate the candidate with the most LAST-place votes. */
function winCoombs(ranks: number[][], m: number): number {
  const alive = new Array(m).fill(true);
  let remaining = m;
  while (remaining > 1) {
    const first = new Array(m).fill(0);
    const last = new Array(m).fill(0);
    for (const r of ranks) {
      const top = r.find((i) => alive[i]);
      if (top !== undefined) first[top] += 1;
      for (let k = r.length - 1; k >= 0; k--)
        if (alive[r[k]]) {
          last[r[k]] += 1;
          break;
        }
    }
    const total = first.reduce((s, x) => s + x, 0);
    const leader = argmax(first);
    if (first[leader] > total / 2) return leader;
    // Eliminate ALL alive candidates tied for the most last-place votes — neutral
    // (candidate-order-independent), matching the backend engine.
    let max = -1;
    for (let i = 0; i < m; i++) if (alive[i] && last[i] > max) max = last[i];
    const doomed: number[] = [];
    for (let i = 0; i < m; i++) if (alive[i] && last[i] === max) doomed.push(i);
    if (doomed.length >= remaining) return -1; // every survivor tied → no winner
    for (const i of doomed) {
      alive[i] = false;
      remaining--;
    }
  }
  return alive.findIndex((a) => a);
}

/** Borda scores counting only candidates still alive. */
function bordaAlive(ranks: number[][], m: number, alive: boolean[]): number[] {
  const k = alive.filter(Boolean).length;
  const score = new Array(m).fill(0);
  for (const r of ranks) {
    let rank = 0;
    for (const c of r)
      if (alive[c]) {
        score[c] += k - 1 - rank;
        rank += 1;
      }
  }
  return score;
}

/** Nanson: iteratively eliminate every candidate with below-average Borda. */
function winNanson(ranks: number[][], m: number): number {
  const alive = new Array(m).fill(true);
  let remaining = m;
  while (remaining > 1) {
    const score = bordaAlive(ranks, m, alive);
    const idx = [];
    for (let i = 0; i < m; i++) if (alive[i]) idx.push(i);
    const avg = idx.reduce((s, i) => s + score[i], 0) / idx.length;
    const elim = idx.filter((i) => score[i] < avg - 1e-9);
    if (elim.length === 0) return idx.reduce((b, i) => (score[i] > score[b] ? i : b), idx[0]);
    for (const i of elim) {
      alive[i] = false;
      remaining -= 1;
    }
  }
  return alive.findIndex((a) => a);
}

/** Baldwin: iteratively eliminate the single lowest-Borda candidate. */
function winBaldwin(ranks: number[][], m: number): number {
  const alive = new Array(m).fill(true);
  let remaining = m;
  while (remaining > 1) {
    const score = bordaAlive(ranks, m, alive);
    let worst = -1;
    for (let i = 0; i < m; i++)
      if (alive[i] && (worst === -1 || score[i] < score[worst])) worst = i;
    alive[worst] = false;
    remaining -= 1;
  }
  return alive.findIndex((a) => a);
}

/**
 * Ranked Pairs (Tideman, 1987): lock the strongest pairwise majorities first,
 * skipping any that would create a cycle; the source of the resulting acyclic
 * tournament wins. Elects the Condorcet winner when one exists, clone-independent.
 */
function winRankedPairs(ranks: number[][], m: number): number {
  const beats = pairwise(ranks, m); // beats[i][j] = voters ranking i above j
  const majorities: { margin: number; support: number; w: number; l: number }[] = [];
  for (let i = 0; i < m; i++) {
    for (let j = i + 1; j < m; j++) {
      const ij = beats[i][j];
      const ji = beats[j][i];
      if (ij > ji) majorities.push({ margin: ij - ji, support: ij, w: i, l: j });
      else if (ji > ij) majorities.push({ margin: ji - ij, support: ji, w: j, l: i });
    }
  }
  // Strongest first: margin desc, then winner support desc, then index order.
  majorities.sort((a, b) => b.margin - a.margin || b.support - a.support || a.w - b.w || a.l - b.l);

  const locked: boolean[][] = Array.from({ length: m }, () => new Array(m).fill(false));
  const reaches = (src: number, dst: number): boolean => {
    const stack = [src];
    const seen = new Array(m).fill(false);
    while (stack.length) {
      const node = stack.pop();
      if (node === undefined) break;
      if (node === dst) return true;
      if (seen[node]) continue;
      seen[node] = true;
      for (let k = 0; k < m; k++) if (locked[node][k]) stack.push(k);
    }
    return false;
  };
  for (const { w, l } of majorities) {
    // w → l would close a cycle iff l can already reach w.
    if (!reaches(l, w)) locked[w][l] = true;
  }
  for (let i = 0; i < m; i++) {
    let incoming = false;
    for (let j = 0; j < m; j++)
      if (locked[j][i]) {
        incoming = true;
        break;
      }
    if (!incoming) return i;
  }
  return winCondorcet(ranks, m); // degenerate fallback (all-tie field)
}

/** STAR: score, then an automatic runoff between the two highest totals. */
function winStar(scores: number[][], m: number): number {
  const total = new Array(m).fill(0);
  for (const s of scores) for (let i = 0; i < m; i++) total[i] += s[i];
  const order = total.map((_, i) => i).sort((a, b) => total[b] - total[a]);
  const [a, b] = [order[0], order[1]];
  let av = 0;
  let bv = 0;
  for (const s of scores) {
    if (s[a] > s[b]) av += 1;
    else if (s[b] > s[a]) bv += 1;
  }
  return av >= bv ? a : b;
}

/** Majority judgment: highest median grade, tie-broken by removing medians. */
function winMajorityJudgment(scores: number[][], m: number): number {
  const L = 6;
  const work: number[][] = Array.from({ length: m }, () => []);
  for (const s of scores) for (let i = 0; i < m; i++) work[i].push(Math.round(s[i] * (L - 1)));
  for (let i = 0; i < m; i++) work[i].sort((x, y) => x - y);
  const lowerMedian = (g: number[]): number => (g.length ? g[Math.floor((g.length - 1) / 2)] : -1);
  let pool = Array.from({ length: m }, (_, i) => i);
  while (pool.length > 1 && work[pool[0]].length > 0) {
    let bestMed = -Infinity;
    for (const c of pool) bestMed = Math.max(bestMed, lowerMedian(work[c]));
    const top = pool.filter((c) => lowerMedian(work[c]) === bestMed);
    if (top.length === 1) return top[0];
    for (const c of top) work[c].splice(Math.floor((work[c].length - 1) / 2), 1);
    pool = top;
  }
  return pool[0];
}

/** Score / evaluative: highest summed cardinal score. */
function winScore(scores: number[][], m: number): number {
  const total = new Array(m).fill(0);
  for (const s of scores) for (let i = 0; i < m; i++) total[i] += s[i];
  return argmax(total);
}

// ── Tier B rules (client-only) ────────────────────────────────────────────────

/** Anti-plurality (veto): elect whoever is ranked LAST the fewest times. */
function winAntiPlurality(ranks: number[][], m: number): number {
  const last = new Array(m).fill(0);
  for (const r of ranks) last[r[r.length - 1]] += 1;
  let best = 0;
  for (let i = 1; i < m; i++) if (last[i] < last[best]) best = i;
  return best;
}

/** Dowdall (Nauru): harmonic positional weights — rank k scores 1/(k+1). */
function winDowdall(ranks: number[][], m: number): number {
  const s = new Array(m).fill(0);
  for (const r of ranks) r.forEach((c, rank) => (s[c] += 1 / (rank + 1)));
  return argmax(s);
}

/** The Condorcet winner (beats every rival head-to-head), or -1 if none exists.
 *  Restrict to `alive` to look only among the remaining candidates. Exported for
 *  the Benham replay (which shows the per-round Condorcet check). */
export function condorcetWinnerIdx(ranks: number[][], m: number, alive?: boolean[]): number {
  const b = pairwise(ranks, m);
  const live = alive ?? new Array(m).fill(true);
  for (let i = 0; i < m; i++) {
    if (!live[i]) continue;
    let beatsAll = true;
    for (let j = 0; j < m; j++)
      if (i !== j && live[j] && !(b[i][j] > b[j][i])) {
        beatsAll = false;
        break;
      }
    if (beatsAll) return i;
  }
  return -1;
}

/** Black: the Condorcet winner when one exists, otherwise the Borda winner. */
function winBlack(ranks: number[][], m: number): number {
  const cw = condorcetWinnerIdx(ranks, m);
  return cw >= 0 ? cw : winBorda(ranks, m);
}

/**
 * The Smith set (GETCHA): the smallest non-empty set of candidates that each
 * beat-or-tie everyone outside it. Restrict to `alive` to compute it on a
 * subprofile. Pairwise margins are ballot-fixed, so the same tally serves any
 * subset. Returns member indices ascending. Exported for the replay animation.
 */
export function smithSet(ranks: number[][], m: number, alive?: boolean[]): number[] {
  const live = alive ?? new Array(m).fill(true);
  const members: number[] = [];
  for (let i = 0; i < m; i++) if (live[i]) members.push(i);
  if (members.length <= 1) return members;
  const b = pairwise(ranks, m);
  const copeland = new Map<number, number>();
  for (const i of members) {
    let s = 0;
    for (const j of members) {
      if (i === j) continue;
      if (b[i][j] > b[j][i]) s += 1;
      else if (b[i][j] < b[j][i]) s -= 1;
    }
    copeland.set(i, s);
  }
  // Grow the smallest Copeland-ordered prefix until it dominates everyone below.
  const order = [...members].sort((x, y) => copeland.get(y)! - copeland.get(x)!);
  for (let k = 1; k <= order.length; k++) {
    const S = new Set(order.slice(0, k));
    let dominant = true;
    for (const i of S) {
      for (const j of members)
        if (!S.has(j) && b[j][i] > b[i][j]) {
          dominant = false;
          break;
        }
      if (!dominant) break;
    }
    if (dominant) return order.slice(0, k).sort((a, c) => a - c);
  }
  return members;
}

/**
 * Smith-IRV (Tideman's Alternative): restrict to the Smith set, eliminate the
 * plurality loser, repeat. Condorcet-consistent and clone-independent.
 */
function winSmithIRV(ranks: number[][], m: number): number {
  const alive = new Array(m).fill(true);
  let remaining = m;
  while (remaining > 1) {
    const S = smithSet(ranks, m, alive);
    if (S.length === 1) return S[0];
    const inS = new Set(S);
    for (let i = 0; i < m; i++)
      if (alive[i] && !inS.has(i)) {
        alive[i] = false;
        remaining -= 1;
      }
    if (remaining === 1) return alive.findIndex((a) => a);
    // IRV step: eliminate ALL alive candidates tied for the fewest first-prefs.
    const fp = pluralityCounts(ranks, alive, m);
    let min = Infinity;
    for (let i = 0; i < m; i++) if (alive[i] && fp[i] < min) min = fp[i];
    const doomed: number[] = [];
    for (let i = 0; i < m; i++) if (alive[i] && fp[i] === min) doomed.push(i);
    if (doomed.length >= remaining) return -1;
    for (const i of doomed) {
      alive[i] = false;
      remaining -= 1;
    }
  }
  return alive.findIndex((a) => a);
}

/**
 * Split Cycle (Holliday & Pacuit, 2021): a defeat is discarded when it is the
 * weakest in a majority cycle. x wins if no retained defeat lands on it — i.e.
 * every defeat a→x is beaten by the strongest majority path from x back to a.
 * Borda breaks a multi-winner Split-Cycle set.
 */
function winSplitCycle(ranks: number[][], m: number): number {
  const b = pairwise(ranks, m);
  const margin = (i: number, j: number): number => b[i][j] - b[j][i];
  // Strongest-path strengths over positive-margin edges (Floyd–Warshall).
  const s = Array.from({ length: m }, () => new Array(m).fill(0));
  for (let i = 0; i < m; i++)
    for (let j = 0; j < m; j++) if (i !== j && margin(i, j) > 0) s[i][j] = margin(i, j);
  for (let k = 0; k < m; k++)
    for (let i = 0; i < m; i++)
      for (let j = 0; j < m; j++)
        if (i !== j && i !== k && j !== k) s[i][j] = Math.max(s[i][j], Math.min(s[i][k], s[k][j]));

  const winners: number[] = [];
  for (let x = 0; x < m; x++) {
    let defeated = false;
    for (let a = 0; a < m; a++)
      if (a !== x && margin(a, x) > 0 && margin(a, x) > s[x][a]) {
        defeated = true;
        break;
      }
    if (!defeated) winners.push(x);
  }
  if (winners.length === 1) return winners[0];
  if (winners.length === 0) return winBorda(ranks, m);
  // Borda tie-break within the Split-Cycle set.
  const bordaScore = new Array(m).fill(0);
  for (const r of ranks) r.forEach((c, rank) => (bordaScore[c] += m - 1 - rank));
  return winners.reduce((best, x) => (bordaScore[x] > bordaScore[best] ? x : best), winners[0]);
}

/**
 * Kemeny-Young: the consensus ranking that most agrees with every ballot (fewest
 * pairwise disagreements). Brute-forces the m! orderings — fine for a handful of
 * candidates; falls back to Borda beyond 8 to avoid factorial blow-up.
 */
function winKemeny(ranks: number[][], m: number): number {
  if (m > 8) return winBorda(ranks, m);
  const b = pairwise(ranks, m);
  let bestFirst = 0;
  let bestScore = -Infinity;
  const perm = Array.from({ length: m }, (_, i) => i);
  const permute = (k: number): void => {
    if (k === m) {
      // Kemeny score of this ordering = agreements over all ordered pairs.
      let score = 0;
      for (let i = 0; i < m; i++) for (let j = i + 1; j < m; j++) score += b[perm[i]][perm[j]];
      if (score > bestScore) {
        bestScore = score;
        bestFirst = perm[0];
      }
      return;
    }
    for (let i = k; i < m; i++) {
      [perm[k], perm[i]] = [perm[i], perm[k]];
      permute(k + 1);
      [perm[k], perm[i]] = [perm[i], perm[k]];
    }
  };
  permute(0);
  return bestFirst;
}

/** Cumulative voting: each voter splits ONE point across candidates in proportion
 *  to their scores (favourites get more, but the budget is shared). Most points wins. */
function winCumulative(scores: number[][], m: number): number {
  const tally = new Array(m).fill(0);
  for (const s of scores) {
    const sum = s.reduce((a, x) => a + x, 0);
    if (sum > 0) for (let i = 0; i < m; i++) tally[i] += s[i] / sum;
  }
  return argmax(tally);
}

/** Maximin (Rawlsian): elect the candidate whose WORST rating across voters is
 *  highest — the least-bad option for the most disadvantaged voter. */
function winMaximin(scores: number[][], m: number): number {
  const worst = new Array(m).fill(Infinity);
  for (const s of scores) for (let i = 0; i < m; i++) worst[i] = Math.min(worst[i], s[i]);
  return argmax(worst);
}

/**
 * Benham (Condorcet-IRV): run IRV, but at the start of each round elect the
 * Condorcet winner among the remaining candidates if one exists. A Condorcet
 * method with IRV's clone-resistance.
 */
function winBenham(ranks: number[][], m: number): number {
  const alive = new Array(m).fill(true);
  let remaining = m;
  while (remaining > 1) {
    const cw = condorcetWinnerIdx(ranks, m, alive);
    if (cw >= 0) return cw;
    const fp = pluralityCounts(ranks, alive, m);
    let min = Infinity;
    for (let i = 0; i < m; i++) if (alive[i] && fp[i] < min) min = fp[i];
    const doomed: number[] = [];
    for (let i = 0; i < m; i++) if (alive[i] && fp[i] === min) doomed.push(i);
    if (doomed.length >= remaining) return -1;
    for (const i of doomed) {
      alive[i] = false;
      remaining -= 1;
    }
  }
  return alive.findIndex((a) => a);
}

/**
 * River (Heitzig): like Ranked Pairs, lock the strongest majorities first — but
 * each candidate accepts at most ONE incoming lock, so the result is a tree.
 * Its root (no incoming lock) wins. Elects the Condorcet winner when one exists.
 */
function winRiver(ranks: number[][], m: number): number {
  const beats = pairwise(ranks, m);
  const majorities: { margin: number; support: number; w: number; l: number }[] = [];
  for (let i = 0; i < m; i++)
    for (let j = i + 1; j < m; j++) {
      const ij = beats[i][j];
      const ji = beats[j][i];
      if (ij > ji) majorities.push({ margin: ij - ji, support: ij, w: i, l: j });
      else if (ji > ij) majorities.push({ margin: ji - ij, support: ji, w: j, l: i });
    }
  majorities.sort((a, b) => b.margin - a.margin || b.support - a.support || a.w - b.w || a.l - b.l);

  const locked: boolean[][] = Array.from({ length: m }, () => new Array(m).fill(false));
  const inLock = new Array(m).fill(false); // does l already have an incoming lock?
  const reaches = (src: number, dst: number): boolean => {
    const stack = [src];
    const seen = new Array(m).fill(false);
    while (stack.length) {
      const node = stack.pop();
      if (node === undefined) break;
      if (node === dst) return true;
      if (seen[node]) continue;
      seen[node] = true;
      for (let k = 0; k < m; k++) if (locked[node][k]) stack.push(k);
    }
    return false;
  };
  for (const { w, l } of majorities) {
    if (inLock[l]) continue; // one parent per candidate
    if (reaches(l, w)) continue; // would close a cycle
    locked[w][l] = true;
    inLock[l] = true;
  }
  const root = inLock.findIndex((v) => !v);
  return root >= 0 ? root : winCondorcet(ranks, m);
}

/** Nash (proportional welfare): maximise the PRODUCT of voter utilities — summed
 *  in log-space to stay numerically stable. Rating a candidate 0 crushes it, so
 *  Nash sits between the utilitarian sum (score) and the Rawlsian min (maximin). */
function winNash(scores: number[][], m: number): number {
  const EPS = 1e-6;
  const acc = new Array(m).fill(0);
  for (const s of scores) for (let i = 0; i < m; i++) acc[i] += Math.log(Math.max(s[i], EPS));
  return argmax(acc);
}

/** Raynaud: repeatedly eliminate the candidate on the losing end of the single
 *  largest pairwise defeat, until one remains. Condorcet-consistent. */
function winRaynaud(ranks: number[][], m: number): number {
  const b = pairwise(ranks, m);
  const alive = new Array(m).fill(true);
  let remaining = m;
  while (remaining > 1) {
    let worstMargin = -Infinity;
    let loser = -1;
    for (let i = 0; i < m; i++)
      for (let j = 0; j < m; j++)
        if (i !== j && alive[i] && alive[j] && b[i][j] - b[j][i] > worstMargin) {
          worstMargin = b[i][j] - b[j][i];
          loser = j;
        }
    if (loser < 0) break;
    alive[loser] = false;
    remaining -= 1;
  }
  return alive.findIndex((a) => a);
}

// ── Public API ────────────────────────────────────────────────────────────────

/**
 * Winning candidate INDEX under the given rule from pre-computed ballots —
 * lets the scorecard inject *modified* ballots (e.g. a strategic-compression
 * manipulation probe). `scores` is required for 'approval' (cardinal rule).
 */
export function ruleWinnerFromRanks(
  ranks: number[][],
  m: number,
  rule: Rule,
  scores?: number[][]
): number {
  if (m === 0 || ranks.length === 0) return -1;
  switch (rule) {
    // Cardinal rules — fall back to plurality if scores weren't supplied.
    case 'approval':
      return scores ? winApproval(scores, m) : winPlurality(ranks, m);
    case 'star':
      return scores ? winStar(scores, m) : winPlurality(ranks, m);
    case 'majority_judgment':
      return scores ? winMajorityJudgment(scores, m) : winPlurality(ranks, m);
    case 'score':
      return scores ? winScore(scores, m) : winPlurality(ranks, m);
    // Ordinal rules.
    case 'plurality':
      return winPlurality(ranks, m);
    case 'two_round':
      return winTwoRound(ranks, m);
    case 'irv':
      return winIRV(ranks, m);
    case 'borda':
      return winBorda(ranks, m);
    case 'condorcet':
      return winCondorcet(ranks, m);
    case 'minimax':
      return winMinimax(ranks, m);
    case 'schulze':
      return winSchulze(ranks, m);
    case 'bucklin':
      return winBucklin(ranks, m);
    case 'coombs':
      return winCoombs(ranks, m);
    case 'nanson':
      return winNanson(ranks, m);
    case 'baldwin':
      return winBaldwin(ranks, m);
    case 'ranked_pairs':
      return winRankedPairs(ranks, m);
    // Random ballot is a lottery; its single representative winner is the most
    // probable outcome — the candidate with the largest first-preference share
    // (i.e. the plurality winner). The full distribution drives the probability lens.
    case 'random_ballot':
      return winPlurality(ranks, m);
    case 'black':
      return winBlack(ranks, m);
    case 'anti_plurality':
      return winAntiPlurality(ranks, m);
    // Tier B extras (client-only; no backend parity).
    case 'dowdall':
      return winDowdall(ranks, m);
    case 'smith_irv':
      return winSmithIRV(ranks, m);
    case 'split_cycle':
      return winSplitCycle(ranks, m);
    case 'kemeny':
      return winKemeny(ranks, m);
    case 'cumulative':
      return scores ? winCumulative(scores, m) : winPlurality(ranks, m);
    case 'maximin':
      return scores ? winMaximin(scores, m) : winPlurality(ranks, m);
    case 'benham':
      return winBenham(ranks, m);
    case 'river':
      return winRiver(ranks, m);
    case 'nash':
      return scores ? winNash(scores, m) : winPlurality(ranks, m);
    case 'raynaud':
      return winRaynaud(ranks, m);
    default:
      return winPlurality(ranks, m);
  }
}

/** Winning candidate INDEX under the given rule over a spatial electorate. */
export function ruleWinner(voters: Pt[], cands: NamedPt[], rule: Rule): number {
  const m = cands.length;
  if (m === 0 || voters.length === 0) return -1;
  return ruleWinnerFromRanks(
    rankings(voters, cands),
    m,
    rule,
    CARDINAL_RULES.has(rule) ? computeScores(voters, cands) : undefined
  );
}

export function fieldWinnerName(voters: Pt[], cands: NamedPt[], rule: Rule): string | null {
  const idx = ruleWinner(voters, cands, rule);
  return idx >= 0 ? cands[idx].name : null;
}

export interface WinRegion {
  n: number;
  /** Number of rows (=== n in 2-D/3-D; 1 in 1-D, a strip along x). */
  rows: number;
  /** Flat row-major winner index per cell; cands.length === the hypothetical entrant H. */
  cells: number[];
}

/**
 * Win/entry-region grid: for each cell, place a hypothetical candidate H there
 * alongside the field and record who wins under the rule. Cells where H wins are
 * the *entry region*; cells coloured by an existing candidate show their basin,
 * and the boundaries expose spoiler-vulnerable territory.
 */
export function winRegionGrid(
  voters: Pt[],
  cands: NamedPt[],
  rule: Rule,
  n: number,
  dims: Dims = 2
): WinRegion {
  // 1-D: a single row swept along x. 2-D/3-D: an n×n x–y grid (in 3-D the
  // hypothetical entrant sits at z=0, so it reads as a z=0 slice of the space).
  const rows = dims === 1 ? 1 : n;
  const cells = new Array(rows * n);
  for (let r = 0; r < rows; r++) {
    const y = dims === 1 ? 0 : 1 - ((r + 0.5) / n) * 2;
    for (let c = 0; c < n; c++) {
      const x = ((c + 0.5) / n) * 2 - 1;
      const field: NamedPt[] = [...cands, { name: 'H', x, y, z: 0 }];
      cells[r * n + c] = ruleWinner(voters, field, rule);
    }
  }
  return { n, rows, cells };
}

export interface ProbRegion {
  n: number;
  rows: number;
  /** Flat row-major P(entrant H wins under random ballot) per cell, in [0,1]. */
  cells: number[];
}

/**
 * Random-ballot win-probability field. For each cell, place a hypothetical
 * entrant H and record the probability it would win under random ballot — i.e.
 * the share of voters whose nearest candidate is H (H's first-preference basin).
 * This is the natural "every basin is a probability" heatmap that distinguishes
 * the lottery from a deterministic rule's hard win-region.
 */
export function randomBallotProbGrid(
  voters: Pt[],
  cands: NamedPt[],
  n: number,
  dims: Dims = 2
): ProbRegion {
  const rows = dims === 1 ? 1 : n;
  const cells = new Array(rows * n).fill(0);
  const denom = voters.length || 1;
  for (let r = 0; r < rows; r++) {
    const y = dims === 1 ? 0 : 1 - ((r + 0.5) / n) * 2;
    for (let c = 0; c < n; c++) {
      const x = ((c + 0.5) / n) * 2 - 1;
      const h: Pt = { x, y, z: 0 };
      let count = 0;
      for (const v of voters) {
        const dh = dist(v, h);
        let nearest = true;
        for (const cand of cands)
          if (dist(v, cand) < dh) {
            nearest = false;
            break;
          }
        if (nearest) count += 1;
      }
      cells[r * n + c] = count / denom;
    }
  }
  return { n, rows, cells };
}

/**
 * Per-candidate win probabilities under random ballot — each existing
 * candidate's first-preference share (nearest-candidate count / voters). Sums to
 * 1 (minus any voters tied to a removed/empty field). Drives the lottery bars.
 */
export function randomBallotShares(voters: Pt[], cands: NamedPt[]): number[] {
  const m = cands.length;
  const counts = new Array(m).fill(0);
  if (m === 0) return counts;
  for (const v of voters) {
    let best = -1;
    let bd = Infinity;
    for (let i = 0; i < m; i++) {
      const d = dist(v, cands[i]);
      if (d < bd) {
        bd = d;
        best = i;
      }
    }
    if (best >= 0) counts[best] += 1;
  }
  const denom = voters.length || 1;
  return counts.map((c) => c / denom);
}

// ── Turnout / abstention (electorate-realism layer) ──────────────────────────
//
// Downsian abstention: a voter stays home either from ALIENATION (even their
// best option is too far — "none of these represent me") or INDIFFERENCE (their
// top two are nearly equidistant — "no real stake"). Both are stated models;
// `intensity` ∈ [0,1] dials how readily voters abstain. Differential turnout
// reshapes the effective electorate and can flip the winner — the point.

export type TurnoutModel = 'full' | 'alienation' | 'indifference';

export interface TurnoutResult {
  voters: Pt[];
  /** Share of the electorate that actually votes, in [0,1]. */
  rate: number;
}

export function applyTurnout(
  voters: Pt[],
  cands: NamedPt[],
  model: TurnoutModel,
  intensity: number
): TurnoutResult {
  if (model === 'full' || intensity <= 0 || cands.length === 0 || !voters.length) {
    return { voters, rate: 1 };
  }
  const k = Math.max(0, Math.min(1, intensity));
  const votes = voters.filter((v) => {
    const ds = cands.map((c) => dist(v, c)).sort((a, b) => a - b);
    if (model === 'alienation') {
      // Abstain if the nearest candidate is beyond a shrinking radius.
      const radius = (1 - k) * 1.5 + 0.2;
      return ds[0] <= radius;
    }
    // indifference: abstain if the top-two are within a growing margin.
    const margin = k * 0.4;
    return ds.length < 2 || ds[1] - ds[0] > margin;
  });
  // The model can thin the electorate but never empty it (keep the demo sane).
  if (votes.length < 2) return { voters, rate: 1 };
  return { voters: votes, rate: votes.length / voters.length };
}

// ── Blank vote (leader mode only) ────────────────────────────────────────────
//
// Distinct from turnout: a blank voter still shows up (counts toward the
// electorate's headcount) but rejects every candidate outright, so their
// ballot carries no preference at all. Modelled the same way as alienation
// turnout — beyond a shrinking radius of every candidate — the same Downsian
// trigger with a different behavioural response (spoil the ballot rather than
// stay home). `intensity` ∈ [0,1] dials how readily voters reach for blank.

export interface BlankSplit {
  /** Voters whose ballot counts toward a candidate. */
  expressed: Pt[];
  blankCount: number;
  /** Blank share of ALL participating voters (expressed + blank). */
  blankShare: number;
}

export function applyBlankVote(
  voters: Pt[],
  cands: NamedPt[],
  enabled: boolean,
  intensity: number
): BlankSplit {
  if (!enabled || intensity <= 0 || cands.length === 0 || !voters.length) {
    return { expressed: voters, blankCount: 0, blankShare: 0 };
  }
  const k = Math.max(0, Math.min(1, intensity));
  const radius = (1 - k) * 1.5 + 0.2;
  const expressed = voters.filter((v) => Math.min(...cands.map((c) => dist(v, c))) <= radius);
  const blankCount = voters.length - expressed.length;
  // Keep the demo sane: never blank out the whole electorate.
  if (expressed.length < 2) return { expressed: voters, blankCount: 0, blankShare: 0 };
  return { expressed, blankCount, blankShare: blankCount / voters.length };
}

// ── Seeded spatial electorate (deterministic from seed/ideology) ──────────────

function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Standard normal via Box–Muller from a uniform PRNG. */
function gauss(rng: () => number, mu: number, sigma: number): number {
  const u = Math.max(rng(), 1e-9);
  const v = rng();
  return mu + sigma * Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

/**
 * Deterministic voter cloud matching the playground's ideology presets, in
 * `dims` dimensions: 1-D collapses y,z to 0; 2-D collapses z; 3-D is full. So
 * the same seed gives the SAME x for 1/2/3-D — the dimension only *adds* axes.
 */
export function sampleVoters(n: number, seed: number, ideology: string, dims: Dims = 2): Pt[] {
  const rng = mulberry32(seed);
  const clamp = (v: number) => Math.max(-1, Math.min(1, v));
  const out: Pt[] = [];
  for (let i = 0; i < n; i++) {
    // Always draw all three axes (constant RNG consumption) so the same seed
    // gives the SAME x for 1/2/3-D — the dimension only *reveals* further axes.
    let x: number;
    let y: number;
    let z: number;
    if (ideology === 'polarized') {
      const left = rng() < 0.5;
      x = gauss(rng, left ? -0.5 : 0.5, 0.22);
      y = gauss(rng, left ? -0.3 : 0.3, 0.3);
      z = gauss(rng, 0, 0.3);
    } else {
      const sigma = ideology === 'centrist' ? 0.25 : 0.45;
      x = gauss(rng, 0, sigma);
      y = gauss(rng, 0, sigma);
      z = gauss(rng, 0, sigma);
    }
    out.push({
      x: clamp(x),
      y: dims >= 2 ? clamp(y) : 0,
      z: dims >= 3 ? clamp(z) : 0,
    });
  }
  return out;
}
