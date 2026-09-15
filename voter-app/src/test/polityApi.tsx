/**
 * test/polityApi.tsx — fake /api/v2/polity responses for the run explorer's tests.
 *
 * Each test file still mocks the client itself (`vi.mock('…/api/client')`, which
 * vitest hoists per file) and hands its GET mock to `servePolity`.
 */
import React from 'react';
import { useLocation } from 'react-router';
import type { Mock } from 'vitest';

export const runSummary = (key: string, runId: string, engine: string | null = 'llm') => ({
  key,
  label: 'fixture',
  relative_path: runId,
  run_id: runId,
  generation: 'checkpointed',
  engine,
  outcome: null,
  population: 40,
  years: 3,
  seed: 42,
  ticks_reached: 12,
  ticks_planned: 12,
});

export const runOverview = (key: string, overrides: Record<string, unknown> = {}) => ({
  key,
  label: 'fixture',
  run_id: key,
  population: 40,
  ticks_per_year: 4,
  last_tick: 12,
  last_checkpoint_tick: 10,
  vote_coverage: 'all',
  unknown_event_types: [],
  projection: { method: 'latent', positions: 'static', axes: [[], []], citizens: [] },
  parties: [],
  citizen_parties: [],
  terms: [],
  timeline: [],
  standings: [],
  elections: [],
  legislative: [],
  motifs: [],
  ...overrides,
});

const runFrame = (tick: number) => ({
  tick,
  partial: tick > 10,
  status: [],
  chamber: [],
  act: [],
  vote: [],
  candidacy: [],
  president: null,
});

// openapi-fetch resolves to { data } or { error }, with the Response beside it.
const ok = (data: unknown) => ({ data, response: { status: 200, headers: new Headers() } });
const failed = (detail: string) => ({
  error: { detail },
  response: { status: 404, headers: new Headers() },
});

export interface PolityResponses {
  runs?: unknown;
  overview?: unknown;
  /** The frame served for a tick; an empty frame by default. */
  frame?: (tick: number) => unknown;
  failRuns?: boolean;
  failRun?: boolean;
}

export function servePolity(
  get: Mock,
  {
    runs = [runSummary('aaaa', 'first'), runSummary('bbbb', 'second', 'deterministic')],
    overview,
    frame = runFrame,
    failRuns,
    failRun,
  }: PolityResponses = {}
): void {
  get.mockImplementation(
    async (
      path: string,
      init: {
        params?: { path?: { run_key?: string }; query?: { from_tick: number; to_tick: number } };
      }
    ) => {
      if (path === '/api/v2/polity/runs') {
        return failRuns ? failed('roots unreadable') : ok({ runs });
      }
      const key = init.params?.path?.run_key ?? '';
      if (path === '/api/v2/polity/runs/{run_key}') {
        return failRun ? failed('run not found') : ok(overview ?? runOverview(key));
      }
      const { from_tick, to_tick } = init.params!.query!;
      return ok({
        key,
        from_tick,
        to_tick,
        frames: Array.from({ length: to_tick - from_tick + 1 }, (_, i) => frame(from_tick + i)),
      });
    }
  );
}

/** Renders nothing; records the router's current search string for assertions. */
export function makeSearchSpy(): { SearchSpy: React.FC; search: () => string } {
  let last = '';
  const SearchSpy: React.FC = () => {
    last = useLocation().search;
    return null;
  };
  return { SearchSpy, search: () => last };
}
