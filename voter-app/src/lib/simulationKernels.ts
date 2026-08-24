/**
 * simulationKernels — the pure computations the simulation Web Worker runs.
 *
 * They used to live inside the React components that display their output
 * (IdeologyHeatmap, MethodSimilarityGraph, MethodRaceBar), which forced the
 * worker to import those components — and with them React, i18next and the UI
 * kit. A worker has no `window`, so importing that graph threw "window is not
 * defined" on worker start-up and killed every dispatch. Keep this file free of
 * React, i18n, DOM and `window`: it must be importable from a worker.
 *
 * The components re-export these symbols, so existing imports (and their unit
 * tests) keep working unchanged.
 */

// ── Heatmap ───────────────────────────────────────────────────────────────────

export const GRID_N = 30;

export interface HeatmapVoter {
  id: number;
  x: number;
  y: number;
}

export interface HeatmapCandidate {
  name: string;
  x: number;
  y: number;
}

export interface GridCell {
  i: number; // column  [0, N)
  j: number; // row     [0, N), j=0 → domain y=-1 (bottom)
  density: number; // voter count
  winnerIdx: number; // index into candidates array (-1 = no winner)
  distRatio: number; // 1st_dist / 2nd_dist — low = contested
  cx: number; // domain x of cell center
  cy: number; // domain y of cell center
}

export interface HeatmapMetrics {
  maxContestedCell: GridCell | null;
  fortressCell: GridCell | null;
  fortressCandidate: string | null;
  maxDensity: number;
}

export function computeGrid(
  voters: HeatmapVoter[],
  candidates: HeatmapCandidate[],
  N = GRID_N
): { cells: GridCell[]; metrics: HeatmapMetrics } {
  // Bucket voters into cells
  const counts = new Int32Array(N * N);
  for (const v of voters) {
    const i = Math.max(0, Math.min(N - 1, Math.floor(((v.x + 1) / 2) * N)));
    const j = Math.max(0, Math.min(N - 1, Math.floor(((v.y + 1) / 2) * N)));
    counts[j * N + i]++;
  }

  const maxDensity = Math.max(1, ...counts);

  const cells: GridCell[] = [];

  for (let j = 0; j < N; j++) {
    for (let i = 0; i < N; i++) {
      const cx = -1 + ((i + 0.5) * 2) / N;
      const cy = -1 + ((j + 0.5) * 2) / N;

      // Nearest-candidate (Voronoi) winner
      let d1 = Infinity,
        d2 = Infinity,
        winnerIdx = -1;
      for (let k = 0; k < candidates.length; k++) {
        const dx = cx - candidates[k].x;
        const dy = cy - candidates[k].y;
        const d = dx * dx + dy * dy;
        if (d < d1) {
          d2 = d1;
          d1 = d;
          winnerIdx = k;
        } else if (d < d2) {
          d2 = d;
        }
      }

      const distRatio = d2 === Infinity ? 1 : Math.sqrt(d1) / Math.sqrt(d2);

      cells.push({
        i,
        j,
        density: counts[j * N + i],
        winnerIdx,
        distRatio,
        cx,
        cy,
      });
    }
  }

  // Metrics — only count populated cells
  const populated = cells.filter((c) => c.density > 0);

  const maxContestedCell =
    populated.length > 0
      ? populated.reduce((best, c) => (c.distRatio < best.distRatio ? c : best))
      : null;

  // Fortress: populated cell with highest density AND largest advantage (distRatio near 0 = dominance)
  const fortressCell =
    populated.length > 0
      ? populated.reduce(
          (best, c) => (c.density > best.density && c.distRatio < 0.5 ? c : best),
          populated[0]
        )
      : null;

  const fortressCandidate =
    fortressCell && fortressCell.winnerIdx >= 0
      ? (candidates[fortressCell.winnerIdx]?.name ?? null)
      : null;

  return { cells, metrics: { maxContestedCell, fortressCell, fortressCandidate, maxDensity } };
}

// ── Method agreement matrix ───────────────────────────────────────────────────

/** Derive a pairwise agreement matrix from streaming winner distributions. */
export function partialResultsToMatrix(
  pr: Record<string, { winner_distribution: Record<string, number> }>
): Record<string, Record<string, number>> {
  const methods = Object.keys(pr);
  const matrix: Record<string, Record<string, number>> = {};
  for (const a of methods) {
    matrix[a] = {};
    for (const b of methods) {
      if (a === b) {
        matrix[a][b] = 1.0;
        continue;
      }
      const da = pr[a].winner_distribution;
      const db = pr[b].winner_distribution;
      const cands = new Set([...Object.keys(da), ...Object.keys(db)]);
      let agreement = 0;
      for (const c of cands) agreement += Math.min(da[c] ?? 0, db[c] ?? 0);
      matrix[a][b] = Math.round(agreement * 100) / 100;
    }
  }
  return matrix;
}

// ── Method race ordering ──────────────────────────────────────────────────────

export interface MethodRow {
  method: string;
  winner: string | null;
  stability: number; // [0, 1]
  rank: number; // 0 = most stable
}

export interface MethodStreamStats {
  winner_distribution: Record<string, number>;
  most_common_winner: string | null;
}

export function sortMethods(partialResults: Record<string, MethodStreamStats>): MethodRow[] {
  return Object.entries(partialResults)
    .map(([method, stats]) => {
      const winner = stats.most_common_winner;
      const stability = winner ? (stats.winner_distribution[winner] ?? 0) : 0;
      return { method, winner, stability, rank: 0 };
    })
    .sort((a, b) => b.stability - a.stability)
    .map((row, i) => ({ ...row, rank: i }));
}
