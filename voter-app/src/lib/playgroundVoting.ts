// playgroundVoting.ts — fast, pure, client-side voting over a SPATIAL electorate
// (Lab reshape P2). Powers the live single-office canvas: an approximate winner +
// the win/entry-region overlay that reflows during drag. The backend profile engine
// remains the source of truth for the precise scorecard on drag-release.
//
// Voter utility for a candidate is -distance (closer = better). Everything derives
// from that: rankings for ordinal rules, per-voter min-max scores for cardinal ones.

export interface NamedPt {
  name: string;
  x: number;
  y: number;
}
export interface Pt {
  x: number;
  y: number;
}

export type Rule =
  | 'plurality'
  | 'two_round'
  | 'irv'
  | 'borda'
  | 'approval'
  | 'condorcet';

export const RULE_LABELS: Record<Rule, string> = {
  plurality: 'Pluralité (1 tour)',
  two_round: 'Deux tours',
  irv: 'Vote alternatif (IRV)',
  borda: 'Borda',
  approval: 'Approbation',
  condorcet: 'Condorcet (Copeland)',
};

const dist = (a: Pt, b: Pt): number => Math.hypot(a.x - b.x, a.y - b.y);

/** Per-voter candidate-index ranking, best→worst (nearest first). */
export function computeRanks(voters: Pt[], cands: Pt[]): number[][] {
  return voters.map((v) => {
    const idx = cands.map((_, i) => i);
    idx.sort((a, b) => dist(v, cands[a]) - dist(v, cands[b]));
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
      if (i === a) { av++; break; }
      if (i === b) { bv++; break; }
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
    // eliminate the alive candidate with the fewest first-prefs
    let worst = -1;
    for (let i = 0; i < m; i++) {
      if (alive[i] && (worst === -1 || counts[i] < counts[worst])) worst = i;
    }
    alive[worst] = false;
    remaining--;
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
    const u = cands.map((c) => -dist(v, c));
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

function winCondorcet(ranks: number[][], m: number): number {
  // Copeland: pairwise wins − losses; ties broken by Borda.
  const beats = Array.from({ length: m }, () => new Array(m).fill(0));
  for (const r of ranks) {
    const pos = new Array(m).fill(0);
    r.forEach((cand, rank) => { pos[cand] = rank; });
    for (let i = 0; i < m; i++) {
      for (let j = i + 1; j < m; j++) {
        if (pos[i] < pos[j]) beats[i][j] += 1;
        else beats[j][i] += 1;
      }
    }
  }
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
    case 'approval': return scores ? winApproval(scores, m) : winPlurality(ranks, m);
    case 'plurality': return winPlurality(ranks, m);
    case 'two_round': return winTwoRound(ranks, m);
    case 'irv': return winIRV(ranks, m);
    case 'borda': return winBorda(ranks, m);
    case 'condorcet': return winCondorcet(ranks, m);
    default: return winPlurality(ranks, m);
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
    rule === 'approval' ? computeScores(voters, cands) : undefined
  );
}

export function fieldWinnerName(voters: Pt[], cands: NamedPt[], rule: Rule): string | null {
  const idx = ruleWinner(voters, cands, rule);
  return idx >= 0 ? cands[idx].name : null;
}

export interface WinRegion {
  n: number;
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
  n: number
): WinRegion {
  const cells = new Array(n * n);
  // A cell value === cands.length means the hypothetical entrant H wins there.
  for (let r = 0; r < n; r++) {
    const y = 1 - ((r + 0.5) / n) * 2;
    for (let c = 0; c < n; c++) {
      const x = ((c + 0.5) / n) * 2 - 1;
      const field: NamedPt[] = [...cands, { name: 'H', x, y }];
      cells[r * n + c] = ruleWinner(voters, field, rule);
    }
  }
  return { n, cells };
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

/** Deterministic voter cloud matching the playground's ideology presets. */
export function sampleVoters(n: number, seed: number, ideology: string): Pt[] {
  const rng = mulberry32(seed);
  const clamp = (x: number) => Math.max(-1, Math.min(1, x));
  const out: Pt[] = [];
  for (let i = 0; i < n; i++) {
    if (ideology === 'polarized') {
      const left = rng() < 0.5;
      const cx = left ? -0.5 : 0.5;
      out.push({ x: clamp(gauss(rng, cx, 0.22)), y: clamp(gauss(rng, left ? -0.3 : 0.3, 0.3)) });
    } else if (ideology === 'centrist') {
      out.push({ x: clamp(gauss(rng, 0, 0.25)), y: clamp(gauss(rng, 0, 0.25)) });
    } else {
      out.push({ x: clamp(gauss(rng, 0, 0.45)), y: clamp(gauss(rng, 0, 0.45)) });
    }
  }
  return out;
}
