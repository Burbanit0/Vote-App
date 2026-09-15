import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import PolityPage from '../PolityPage';
import { makeTestQueryClient } from '../../test/queryWrapper';
import { PolityProvider, usePolityCtx } from '../../components/polity/PolityController';

vi.mock('../../api/client', () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn(), PATCH: vi.fn() },
}));
const { apiClient } = (await import('../../api/client')) as unknown as {
  apiClient: { GET: ReturnType<typeof vi.fn> };
};

const run = (key: string, runId: string, engine = 'llm') => ({
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

const overview = (key: string, voteCoverage = 'all') => ({
  key,
  label: 'fixture',
  run_id: key,
  population: 40,
  ticks_per_year: 4,
  last_tick: 12,
  last_checkpoint_tick: 10,
  vote_coverage: voteCoverage,
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
});

const frame = (tick: number) => ({
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

type Responses = { runs?: unknown; overview?: unknown; failRuns?: boolean; failRun?: boolean };

function serve({
  runs = [run('aaaa', 'first'), run('bbbb', 'second', 'deterministic')],
  overview: body,
  failRuns,
  failRun,
}: Responses) {
  apiClient.GET.mockImplementation(
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
        return failRun ? failed('run not found') : ok(body ?? overview(key));
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

let lastSearch = '';
const SearchSpy: React.FC = () => {
  lastSearch = useLocation().search;
  return null;
};

function renderAt(url: string) {
  return render(
    <QueryClientProvider client={makeTestQueryClient()}>
      <MemoryRouter initialEntries={[url]}>
        <PolityPage />
        <SearchSpy />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('PolityPage', () => {
  beforeEach(() => {
    apiClient.GET.mockReset();
    lastSearch = '';
  });

  it('shows the first run listed, its facts and where the player stands', async () => {
    serve({});
    renderAt('/polity');
    expect(screen.getByTestId('polity-page')).toBeInTheDocument();
    expect(screen.getByTestId('polity-runs-loading')).toHaveTextContent('Loading runs');

    expect(await screen.findByTestId('polity-fact-population')).toHaveTextContent('40 citizens');
    expect(screen.getByRole('heading', { name: 'Run explorer' })).toBeInTheDocument();
    expect(screen.getByTestId('polity-run-picker')).toHaveValue('aaaa');
    expect(screen.getByTestId('polity-fact-duration')).toHaveTextContent('3 years · 13 ticks');
    expect(screen.getByTestId('polity-fact-engine')).toHaveTextContent('language model');
    expect(screen.getByTestId('polity-fact-votes')).toHaveTextContent('all');
    await waitFor(() =>
      expect(screen.getByTestId('polity-fact-tick')).toHaveTextContent('Year 1 · Q1')
    );
    expect(screen.getByTestId('polity-fact-tick')).not.toHaveTextContent('unconfirmed');
  });

  it('reads the tick from the URL, clamps it to the run and marks an unconfirmed tick', async () => {
    serve({});
    renderAt('/polity?run=bbbb&tick=99');
    expect(await screen.findByTestId('polity-fact-engine')).toHaveTextContent(
      'deterministic rules'
    );
    await waitFor(() =>
      expect(screen.getByTestId('polity-fact-tick')).toHaveTextContent('Year 4 · Q1 — unconfirmed')
    );
    expect(apiClient.GET).toHaveBeenCalledWith(
      '/api/v2/polity/runs/{run_key}/frames',
      expect.objectContaining({
        params: { path: { run_key: 'bbbb' }, query: { from_tick: 0, to_tick: 12 } },
      })
    );
  });

  it('switching runs starts the new run from its first tick with nobody selected', async () => {
    serve({});
    renderAt('/polity?run=aaaa&tick=9&citizen=3&lens=vote');
    const picker = await screen.findByTestId('polity-run-picker');
    await screen.findByTestId('polity-run-facts');
    fireEvent.change(picker, { target: { value: 'bbbb' } });
    await waitFor(() => expect(lastSearch).toBe('?run=bbbb&lens=vote'));
    expect(await screen.findByTestId('polity-fact-engine')).toHaveTextContent(
      'deterministic rules'
    );
  });

  it('names each audit and missing vote coverage', async () => {
    serve({ overview: overview('aaaa', 'audit_sample') });
    renderAt('/polity');
    expect(await screen.findByTestId('polity-fact-votes')).toHaveTextContent('audit sample');
  });

  it('says when there is no run to explore', async () => {
    serve({ runs: [] });
    renderAt('/polity');
    expect(await screen.findByTestId('polity-no-runs')).toHaveTextContent('No run to explore');
    expect(screen.queryByTestId('polity-run-picker')).not.toBeInTheDocument();
  });

  it('reports a list or a run that cannot be loaded', async () => {
    serve({ failRuns: true });
    const { unmount } = renderAt('/polity');
    expect(await screen.findByTestId('polity-runs-error')).toHaveTextContent('roots unreadable');
    unmount();

    serve({ failRun: true });
    renderAt('/polity');
    expect(await screen.findByTestId('polity-run-error')).toHaveTextContent('run not found');
  });
});

describe('PolityProvider', () => {
  beforeEach(() => {
    apiClient.GET.mockReset();
    lastSearch = '';
  });

  it('writes the tick, lens and citizen its consumers set into the URL', async () => {
    serve({});
    const Probe: React.FC = () => {
      const ctx = usePolityCtx();
      return (
        <div>
          <span data-testid="probe-state">{`${ctx.tick}|${ctx.lens}|${ctx.citizen}`}</span>
          <button onClick={() => ctx.setTick(99)}>tick</button>
          <button onClick={() => ctx.setLens('vote')}>lens</button>
          <button onClick={() => ctx.setCitizen(3)}>citizen</button>
          <button onClick={() => ctx.setCitizen(null)}>nobody</button>
        </div>
      );
    };
    render(
      <QueryClientProvider client={makeTestQueryClient()}>
        <MemoryRouter initialEntries={['/polity']}>
          <PolityProvider>
            <Probe />
          </PolityProvider>
          <SearchSpy />
        </MemoryRouter>
      </QueryClientProvider>
    );
    await waitFor(() =>
      expect(screen.getByTestId('probe-state')).toHaveTextContent('0|activity|null')
    );
    await waitFor(() =>
      expect(apiClient.GET).toHaveBeenCalledWith('/api/v2/polity/runs/{run_key}', expect.anything())
    );
    await waitFor(() =>
      expect(screen.getByTestId('probe-state')).toHaveTextContent('0|activity|null')
    );
    fireEvent.click(screen.getByText('tick'));
    fireEvent.click(screen.getByText('lens'));
    fireEvent.click(screen.getByText('citizen'));
    await waitFor(() => expect(lastSearch).toBe('?tick=12&lens=vote&citizen=3'));
    expect(screen.getByTestId('probe-state')).toHaveTextContent('12|vote|3');
    fireEvent.click(screen.getByText('nobody'));
    await waitFor(() => expect(lastSearch).toBe('?tick=12&lens=vote'));
  });

  it('shows placeholders for what a run summary leaves out', async () => {
    serve({
      runs: [{ ...run('aaaa', 'bare'), engine: null, population: null, years: null, seed: null }],
    });
    renderAt('/polity');
    expect(await screen.findByTestId('polity-fact-engine')).toHaveTextContent('—');
    expect(screen.getByTestId('polity-run-picker')).toHaveTextContent(
      'bare — ? citizens, ? years, seed ?'
    );
  });

  it('shows an error that carries no detail as text', async () => {
    apiClient.GET.mockResolvedValue({
      error: 'unreachable',
      response: { status: 502, headers: new Headers() },
    });
    renderAt('/polity');
    expect(await screen.findByTestId('polity-runs-error')).toHaveTextContent('unreachable');
  });
});

describe('usePolityCtx', () => {
  it('refuses to run outside its provider', () => {
    const Orphan: React.FC = () => {
      usePolityCtx();
      return null;
    };
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => render(<Orphan />)).toThrow('usePolityCtx must be used inside <PolityProvider>');
    spy.mockRestore();
  });
});
