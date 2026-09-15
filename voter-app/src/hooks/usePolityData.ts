/**
 * hooks/usePolityData.ts — the run explorer's data, over the typed API.
 *
 * A finished run does not change while it is being read (the server reloads a
 * run only when its journal changes on disk), so its responses never go stale
 * within a visit. Frames arrive in fixed chunks (lib/polity/ticks.ts), one query
 * per chunk, so scrubbing inside a chunk costs nothing and chunks cache apart.
 */
import { $api } from '../api/hooks';
import type { components } from '../api/types.gen';
import { chunkOf } from '../lib/polity/ticks';

export type PolityRunSummary = components['schemas']['PolityRunSummary'];
export type PolityRunOverview = components['schemas']['PolityRunOverview'];
export type PolityFrame = components['schemas']['PolityFrame'];

const IMMUTABLE = { staleTime: Infinity } as const;

export function usePolityRuns() {
  return $api.useQuery('get', '/api/v2/polity/runs', {}, IMMUTABLE);
}

export function usePolityRun(runKey: string | null) {
  return $api.useQuery(
    'get',
    '/api/v2/polity/runs/{run_key}',
    { params: { path: { run_key: runKey ?? '' } } },
    { ...IMMUTABLE, enabled: runKey !== null }
  );
}

/** The frame of `tick`, loaded with the rest of its chunk. */
export function usePolityFrame(runKey: string | null, tick: number, lastTick: number | null) {
  const chunk = chunkOf(tick, lastTick ?? tick);
  const query = $api.useQuery(
    'get',
    '/api/v2/polity/runs/{run_key}/frames',
    {
      params: {
        path: { run_key: runKey ?? '' },
        query: { from_tick: chunk.from, to_tick: chunk.to },
      },
    },
    { ...IMMUTABLE, enabled: runKey !== null && lastTick !== null }
  );
  const frame: PolityFrame | undefined = query.data?.frames[tick - chunk.from];
  return { frame, isLoading: query.isLoading, error: query.error };
}

export type PolityCitizen = components['schemas']['PolityCitizen'];

/** A citizen's biography in the shown run. */
export function usePolityCitizen(runKey: string, citizen: number) {
  return $api.useQuery(
    'get',
    '/api/v2/polity/runs/{run_key}/citizens/{citizen_id}',
    { params: { path: { run_key: runKey, citizen_id: citizen } } },
    IMMUTABLE
  );
}
