import { useCallback, useEffect, useRef, useState } from 'react';
import { runComparisonSimulation, InformationModelConfig } from '../services/simulationCompareApi';
import { SimulationCompareResult } from '../types';

export interface DebouncedSimulationParams {
  num_voters: number;
  candidates: string[];
  ideology_distribution: string;
  information_model?: InformationModelConfig;
}

export interface UseDebouncedSimulationResult {
  results: SimulationCompareResult[];
  loading: boolean;
  error: string | null;
  lastUpdated: Date | null;
  runNow: () => void;
}

/**
 * Runs POST /simulations/compare automatically after a debounce period
 * whenever params change. Prevents race conditions via a run-ID counter —
 * results from a superseded request are silently discarded.
 *
 * Behaviour:
 *   - First render: fires immediately (no debounce)
 *   - Candidate count change: clears results instantly, then debounces
 *   - Other param changes: keeps old results at caller's discretion, debounces
 *   - runNow(): skips the debounce and fires immediately
 */
export function useDebouncedSimulation(
  params: DebouncedSimulationParams,
  numSimulations: number,
  debounceMs = 600
): UseDebouncedSimulationResult {
  const [results, setResults] = useState<SimulationCompareResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // Use refs to always read latest values inside the async callback
  // without adding them to dependency arrays.
  const paramsRef = useRef(params);
  const numSimRef = useRef(numSimulations);
  useEffect(() => {
    paramsRef.current = params;
  }, [params]);
  useEffect(() => {
    numSimRef.current = numSimulations;
  }, [numSimulations]);

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const runIdRef = useRef(0);
  const isFirstRun = useRef(true);
  const prevCandidateCount = useRef(params.candidates.length);

  // Serialise candidates so useEffect can detect renames without counting
  const candidatesKey = params.candidates.join('\x00');

  const doRun = useCallback(async () => {
    const p = paramsRef.current;
    const n = numSimRef.current;

    if (p.candidates.length < 2) {
      setResults([]);
      setLoading(false);
      return;
    }

    const myRunId = ++runIdRef.current;
    setLoading(true);
    setError(null);

    try {
      const simParams = {
        num_voters: p.num_voters,
        candidates: p.candidates,
        ideology_distribution: p.ideology_distribution,
        ...(p.information_model?.enabled ? { information_model: p.information_model } : {}),
      };

      const runs = await Promise.all(
        Array.from({ length: n }, () => runComparisonSimulation(simParams))
      );

      if (runIdRef.current !== myRunId) return; // stale — a newer run is in progress
      setResults(runs);
      setLastUpdated(new Date());
      setError(null);
    } catch (e) {
      if (runIdRef.current !== myRunId) return;
      setError(e instanceof Error ? e.message : 'Simulation failed');
    } finally {
      if (runIdRef.current === myRunId) setLoading(false);
    }
  }, []); // deliberately empty — reads from refs

  useEffect(() => {
    const currentCount = params.candidates.length;
    const countChanged = currentCount !== prevCandidateCount.current;
    prevCandidateCount.current = currentCount;

    if (countChanged) {
      // Candidate added or removed → clear results immediately
      runIdRef.current++; // invalidate any in-flight request
      setResults([]);
      setError(null);
    }

    if (params.candidates.length < 2) return;

    if (timerRef.current) clearTimeout(timerRef.current);

    if (isFirstRun.current) {
      isFirstRun.current = false;
      doRun();
      return;
    }

    timerRef.current = setTimeout(doRun, debounceMs);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [
    candidatesKey,
    params.num_voters,
    params.ideology_distribution,
    params.information_model?.enabled,
    numSimulations,
    debounceMs,
    doRun,
  ]);

  const runNow = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    doRun();
  }, [doRun]);

  return { results, loading, error, lastUpdated, runNow };
}
