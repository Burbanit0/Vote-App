import React from 'react';
import type { Mock } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import PolityPage from '../../../pages/PolityPage';
import { makeTestQueryClient } from '../../../test/queryWrapper';
import { makeSearchSpy, runOverview, servePolity } from '../../../test/polityApi';

vi.mock('../../../api/client', () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn(), PATCH: vi.fn() },
}));
const { apiClient } = (await import('../../../api/client')) as unknown as {
  apiClient: { GET: Mock };
};

// Recharts, mocked: records that it was imported, and lets a test click a chart
// as if on a tick.
const recharts = vi.hoisted(() => ({
  imported: false,
  clicks: [] as ((state: unknown) => void)[],
}));
vi.mock('recharts', () => {
  recharts.imported = true;
  const Chart = ({
    children,
    onClick,
  }: {
    children?: React.ReactNode;
    onClick?: (state: unknown) => void;
  }) => {
    if (onClick) recharts.clicks.push(onClick);
    return <div data-testid="chart">{children}</div>;
  };
  return {
    ResponsiveContainer: ({ children }: { children?: React.ReactNode }) => <div>{children}</div>,
    LineChart: Chart,
    BarChart: Chart,
    CartesianGrid: () => null,
    Legend: () => null,
    Tooltip: () => null,
    XAxis: () => null,
    YAxis: () => null,
    Line: ({ name }: { name: string }) => <span data-testid="line">{name}</span>,
    Bar: ({ name }: { name: string }) => <span data-testid="bar">{name}</span>,
    ReferenceLine: ({ x }: { x: number }) => <span data-testid="marker">{x}</span>,
  };
});

const spy = makeSearchSpy();

const story = (overrides: Record<string, unknown> = {}) =>
  runOverview('aaaa', {
    standings: [
      {
        tick: 0,
        president: null,
        legitimacy: null,
        ecart: null,
        mandate_strength: null,
        acts: [0, 0, 0, 0, 0],
      },
      {
        tick: 1,
        president: 2,
        legitimacy: 0.6,
        ecart: 0.02,
        mandate_strength: 0.7,
        acts: [3, 1, 0, 2, 5],
      },
    ],
    elections: [
      {
        tick: 0,
        outcome: 'elected',
        winner: 2,
        forced: false,
        turnout: 0.75,
        blank_share: 0.1,
        blank_source: 'audit_sample',
      },
      {
        tick: 4,
        outcome: 'invalidated',
        winner: null,
        forced: false,
        turnout: null,
        blank_share: 0.6,
        blank_source: 'invalidation_check',
      },
      {
        tick: 8,
        outcome: 'no_winner',
        winner: null,
        forced: true,
        turnout: null,
        blank_share: null,
        blank_source: null,
      },
      {
        tick: 12,
        outcome: 'elected',
        winner: 5,
        forced: false,
        turnout: 1,
        blank_share: 0,
        blank_source: 'ballots',
      },
    ],
    ...overrides,
  });

async function renderPage(url = '/polity?tick=3', overview = story()) {
  servePolity(apiClient.GET, { overview });
  render(
    <QueryClientProvider client={makeTestQueryClient()}>
      <MemoryRouter initialEntries={[url]}>
        <PolityPage />
        <spy.SearchSpy />
      </MemoryRouter>
    </QueryClientProvider>
  );
  return screen.findByTestId('polity-macro-toggle');
}

describe('MacroCurves', () => {
  beforeEach(() => {
    apiClient.GET.mockReset();
    recharts.clicks.length = 0;
  });

  it('keeps Recharts out of first paint, fetches it on hover and mounts it on open', async () => {
    const toggle = await renderPage();
    expect(screen.queryByTestId('polity-macro-panel')).not.toBeInTheDocument();
    expect(recharts.imported).toBe(false);

    fireEvent.mouseEnter(toggle);
    await waitFor(() => expect(recharts.imported).toBe(true));
    expect(screen.queryByTestId('polity-macro-panel')).not.toBeInTheDocument();

    fireEvent.click(toggle);
    const panel = await screen.findByTestId('polity-macro-panel');
    expect(
      within(panel)
        .getAllByTestId('line')
        .map((l) => l.textContent)
    ).toEqual(['Legitimacy', 'Mandate strength', 'Gap from the pledge']);
    expect(
      within(panel)
        .getAllByTestId('bar')
        .map((b) => b.textContent)
    ).toEqual([
      'does nothing',
      'signs a petition',
      'launches a petition',
      'mobilizes',
      'waits for the election',
    ]);
    expect(
      within(panel)
        .getAllByTestId('marker')
        .map((m) => m.textContent)
    ).toEqual(['3', '3']);
  });

  it('lists each election with its turnout and blank share, and where that share comes from', async () => {
    fireEvent.click(await renderPage());
    await screen.findByTestId('polity-macro-panel');
    const row = (tick: number) => screen.getByTestId(`polity-election-${tick}`);
    expect(row(0)).toHaveTextContent('0elected275 %10 %audit sample');
    expect(row(4)).toHaveTextContent('4invalidated—unavailable60 %invalidation check');
    expect(row(8)).toHaveTextContent('8no winner—unavailableunavailableunavailable');
    expect(row(12)).toHaveTextContent('12elected5100 %0 %every ballot');

    fireEvent.click(within(row(8)).getByRole('button', { name: '8' }));
    await waitFor(() => expect(new URLSearchParams(spy.search()).get('tick')).toBe('8'));
  });

  it('moves the player to a clicked tick', async () => {
    fireEvent.click(await renderPage());
    await screen.findByTestId('polity-macro-panel');
    recharts.clicks[0]({ activeLabel: 'nowhere' });
    recharts.clicks[1]({ activeLabel: 11 });
    await waitFor(() => expect(new URLSearchParams(spy.search()).get('tick')).toBe('11'));
  });

  it('says when nobody governed and when no election was held', async () => {
    const quiet = story({ standings: [{ tick: 0, acts: [0, 0, 0, 0, 0] }], elections: [] });
    fireEvent.click(await renderPage('/polity', quiet));
    const panel = await screen.findByTestId('polity-macro-panel');
    expect(panel).toHaveTextContent('No reading: nobody governed during this run.');
    expect(panel).toHaveTextContent('No presidential election in this run.');
  });
});
