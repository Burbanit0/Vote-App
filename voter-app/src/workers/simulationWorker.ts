/**
 * simulationWorker.ts — Offloads CPU-heavy frontend computations off the
 * main thread so the UI never freezes during large simulations.
 *
 * Handled tasks:
 *   COMPUTE_HEATMAP  — 30×30 grid density + Voronoi winner (O(N_voters + N²))
 *   COMPUTE_MATRIX   — inter-method agreement from streaming partial results
 *   SORT_MC_RESULTS  — sort Monte Carlo method rows by a given key
 *
 * Every message must carry a unique `id` string; the worker echoes it back
 * so the hook can resolve the matching Promise.
 */

// Kernels only — importing the components that display these results would drag
// React/i18n into the worker, where `window` does not exist.
import {
  computeGrid,
  partialResultsToMatrix,
  sortMethods,
  type HeatmapVoter,
  type HeatmapCandidate,
  type GridCell,
  type HeatmapMetrics,
  type MethodStreamStats,
  type MethodRow,
} from '../lib/simulationKernels';

// ── Message types ─────────────────────────────────────────────────────────────

export type WorkerRequest =
  | {
      id: string;
      type: 'COMPUTE_HEATMAP';
      voters: HeatmapVoter[];
      candidates: HeatmapCandidate[];
      gridN?: number;
    }
  | {
      id: string;
      type: 'COMPUTE_MATRIX';
      partialResults: Record<string, MethodStreamStats>;
    }
  | {
      id: string;
      type: 'SORT_MC_RESULTS';
      partialResults: Record<string, MethodStreamStats>;
    };

export type WorkerResponse =
  | {
      id: string;
      type: 'HEATMAP_DONE';
      cells: GridCell[];
      metrics: HeatmapMetrics;
    }
  | {
      id: string;
      type: 'MATRIX_DONE';
      matrix: Record<string, Record<string, number>>;
    }
  | {
      id: string;
      type: 'SORT_DONE';
      rows: MethodRow[];
    }
  | {
      id: string;
      type: 'ERROR';
      error: string;
    };

// ── Handler ───────────────────────────────────────────────────────────────────

self.addEventListener('message', (event: MessageEvent<WorkerRequest>) => {
  const msg = event.data;

  try {
    switch (msg.type) {
      case 'COMPUTE_HEATMAP': {
        const { cells, metrics } = computeGrid(msg.voters, msg.candidates, msg.gridN);
        const response: WorkerResponse = { id: msg.id, type: 'HEATMAP_DONE', cells, metrics };
        (self as unknown as Worker).postMessage(response);
        break;
      }

      case 'COMPUTE_MATRIX': {
        const matrix = partialResultsToMatrix(msg.partialResults);
        const response: WorkerResponse = { id: msg.id, type: 'MATRIX_DONE', matrix };
        (self as unknown as Worker).postMessage(response);
        break;
      }

      case 'SORT_MC_RESULTS': {
        const rows = sortMethods(msg.partialResults);
        const response: WorkerResponse = { id: msg.id, type: 'SORT_DONE', rows };
        (self as unknown as Worker).postMessage(response);
        break;
      }

      default: {
        const response: WorkerResponse = {
          id: (msg as WorkerRequest).id,
          type: 'ERROR',
          error: `Unknown message type: ${(msg as WorkerRequest).type}`,
        };
        (self as unknown as Worker).postMessage(response);
      }
    }
  } catch (err) {
    const response: WorkerResponse = {
      id: msg.id,
      type: 'ERROR',
      error: String(err),
    };
    (self as unknown as Worker).postMessage(response);
  }
});
