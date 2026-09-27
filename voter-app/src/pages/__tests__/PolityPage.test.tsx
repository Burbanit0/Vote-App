import React from 'react';
import type { Mock } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import PolityPage from '../PolityPage';
import { makeTestQueryClient } from '../../test/queryWrapper';
import {
  makeSearchSpy,
  runOverview,
  runSummary,
  servePolity,
  type PolityResponses,
} from '../../test/polityApi';
import { PolityProvider, usePolityCtx } from '../../components/polity/PolityController';

vi.mock('../../api/client', () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn(), PATCH: vi.fn() },
}));
const { apiClient } = (await import('../../api/client')) as unknown as {
  apiClient: { GET: Mock };
};

const run = runSummary;
const overview = (key: string, voteCoverage = 'all') =>
  runOverview(key, { vote_coverage: voteCoverage });
const serve = (responses: PolityResponses) => servePolity(apiClient.GET, responses);
const spy = makeSearchSpy();
const SearchSpy = spy.SearchSpy;

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
    await waitFor(() => expect(spy.search()).toBe('?run=bbbb&lens=vote'));
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
    await waitFor(() => expect(spy.search()).toBe('?tick=12&lens=vote&citizen=3'));
    expect(screen.getByTestId('probe-state')).toHaveTextContent('12|vote|3');
    fireEvent.click(screen.getByText('nobody'));
    await waitFor(() => expect(spy.search()).toBe('?tick=12&lens=vote'));
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
