/**
 * useSimulationWorker — typed React hook for the simulation Web Worker.
 *
 * Singleton worker (one instance per app lifetime, created lazily on first use).
 * Each dispatch() call returns a Promise resolved when the worker replies.
 * A message queue prevents race conditions when multiple requests are in-flight.
 *
 * Usage:
 *   const { dispatch, isComputing } = useSimulationWorker();
 *   const { cells, metrics } = await dispatch('COMPUTE_HEATMAP', { voters, candidates });
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import type { WorkerRequest, WorkerResponse } from '../workers/simulationWorker';
import type { HeatmapVoter, HeatmapCandidate, GridCell, HeatmapMetrics } from '../components/Simulation/IdeologyHeatmap';
import type { MethodStreamStats } from './useMonteCarloStream';
import type { MethodRow } from '../components/Simulation/MethodRaceBar';

// ── Singleton worker (created once per page, shared across all hook instances)

let _worker: Worker | null = null;
let _pendingCount = 0;

function getWorker(): Worker {
  if (!_worker) {
    _worker = new Worker(
      new URL('../workers/simulationWorker.ts', import.meta.url),
      { type: 'module' },
    );
  }
  return _worker;
}

// Pending promise registry: id → {resolve, reject}
const _pending = new Map<string, { resolve: (v: unknown) => void; reject: (e: unknown) => void }>();
let _listenerAttached = false;

function attachListener() {
  if (_listenerAttached) return;
  _listenerAttached = true;
  getWorker().addEventListener('message', (event: MessageEvent<WorkerResponse>) => {
    const msg = event.data;
    const entry = _pending.get(msg.id);
    if (!entry) return;
    _pending.delete(msg.id);
    _pendingCount = Math.max(0, _pendingCount - 1);
    if (msg.type === 'ERROR') {
      entry.reject(new Error(msg.error));
    } else {
      entry.resolve(msg);
    }
  });
}

// ── Return-type overloads ──────────────────────────────────────────────────────

type DispatchMap = {
  COMPUTE_HEATMAP:  { voters: HeatmapVoter[]; candidates: HeatmapCandidate[]; gridN?: number };
  COMPUTE_MATRIX:   { partialResults: Record<string, MethodStreamStats> };
  SORT_MC_RESULTS:  { partialResults: Record<string, MethodStreamStats> };
};

type ResultMap = {
  COMPUTE_HEATMAP:  { cells: GridCell[]; metrics: HeatmapMetrics };
  COMPUTE_MATRIX:   { matrix: Record<string, Record<string, number>> };
  SORT_MC_RESULTS:  { rows: MethodRow[] };
};

// ── Hook ──────────────────────────────────────────────────────────────────────

export interface UseSimulationWorkerReturn {
  dispatch<K extends keyof DispatchMap>(type: K, payload: DispatchMap[K]): Promise<ResultMap[K]>;
  isComputing: boolean;
}

export function useSimulationWorker(): UseSimulationWorkerReturn {
  const [isComputing, setIsComputing] = useState(false);
  const inflightRef = useRef(0);

  useEffect(() => {
    attachListener();
    // Don't terminate the worker on unmount — it's a singleton shared app-wide
  }, []);

  const dispatch = useCallback(
    <K extends keyof DispatchMap>(type: K, payload: DispatchMap[K]): Promise<ResultMap[K]> => {
      const id = `${type}-${Date.now()}-${Math.random().toString(36).slice(2)}`;

      inflightRef.current += 1;
      _pendingCount += 1;
      setIsComputing(true);

      const promise = new Promise<ResultMap[K]>((resolve, reject) => {
        _pending.set(id, {
          resolve: (v) => {
            inflightRef.current = Math.max(0, inflightRef.current - 1);
            if (inflightRef.current === 0) setIsComputing(false);
            resolve(v as ResultMap[K]);
          },
          reject: (e) => {
            inflightRef.current = Math.max(0, inflightRef.current - 1);
            if (inflightRef.current === 0) setIsComputing(false);
            reject(e);
          },
        });
      });

      const message: WorkerRequest = { id, type, ...payload } as WorkerRequest;
      getWorker().postMessage(message);

      return promise;
    },
    [],
  );

  return { dispatch, isComputing };
}
