import React, { createContext, useContext } from 'react';
import { useSearchParams } from 'react-router';
import {
  usePolityFrame,
  usePolityRun,
  usePolityRuns,
  type PolityFrame,
  type PolityRunOverview,
  type PolityRunSummary,
} from '../../hooks/usePolityData';
import { clampTick, parseTickParam } from '../../lib/polity/ticks';
import { parseCitizen, parseLens, pickRun, type PolityLens } from '../../lib/polity/urlState';

// PolityController — the run explorer's single source of truth, like the
// Playground's controller: what is shown lives in the URL (run, tick, lens,
// citizen), the data comes from the API hooks, and the page's panels read both
// through one context instead of a prop chain.

export interface PolityCtx {
  runs: PolityRunSummary[] | undefined;
  runsLoading: boolean;
  runsError: unknown;
  run: PolityRunSummary | undefined;
  runKey: string | null;
  setRunKey: (key: string) => void;
  overview: PolityRunOverview | undefined;
  overviewLoading: boolean;
  overviewError: unknown;
  tick: number;
  setTick: (tick: number) => void;
  lens: PolityLens;
  setLens: (lens: PolityLens) => void;
  citizen: number | null;
  setCitizen: (citizen: number | null) => void;
  frame: PolityFrame | undefined;
  frameLoading: boolean;
}

const Ctx = createContext<PolityCtx | null>(null);

function useController(): PolityCtx {
  const [params, setParams] = useSearchParams();
  const runsQuery = usePolityRuns();
  const runs = runsQuery.data?.runs;
  const runKey = pickRun(
    params.get('run'),
    (runs ?? []).map((r) => r.key)
  );
  const overviewQuery = usePolityRun(runKey);
  const overview = overviewQuery.data;
  const lastTick = overview?.last_tick ?? null;
  const tick = clampTick(parseTickParam(params.get('tick')) ?? 0, lastTick ?? 0);
  const { frame, isLoading: frameLoading } = usePolityFrame(runKey, tick, lastTick);

  const update = React.useCallback(
    (changes: Record<string, string | null>) =>
      setParams(
        (current) => {
          const next = new URLSearchParams(current);
          for (const [name, value] of Object.entries(changes)) {
            if (value === null) next.delete(name);
            else next.set(name, value);
          }
          return next;
        },
        { replace: true }
      ),
    [setParams]
  );

  return {
    runs,
    runsLoading: runsQuery.isLoading,
    runsError: runsQuery.error,
    run: runs?.find((r) => r.key === runKey),
    runKey,
    // Another run starts from its first tick, with nobody selected.
    setRunKey: (key) => update({ run: key, tick: null, citizen: null }),
    overview,
    overviewLoading: overviewQuery.isLoading,
    overviewError: overviewQuery.error,
    tick,
    setTick: (next) => update({ tick: String(clampTick(next, lastTick ?? 0)) }),
    lens: parseLens(params.get('lens')),
    setLens: (next) => update({ lens: next }),
    citizen: parseCitizen(params.get('citizen'), overview?.population ?? 0),
    setCitizen: (next) => update({ citizen: next === null ? null : String(next) }),
    frame,
    frameLoading,
  };
}

export const PolityProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <Ctx.Provider value={useController()}>{children}</Ctx.Provider>
);

export function usePolityCtx(): PolityCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('usePolityCtx must be used inside <PolityProvider>');
  return ctx;
}
