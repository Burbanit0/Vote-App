import React from 'react';
import type { Mock } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
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

const spy = makeSearchSpy();

async function renderPlayer(url = '/polity') {
  servePolity(apiClient.GET);
  render(
    <QueryClientProvider client={makeTestQueryClient()}>
      <MemoryRouter initialEntries={[url]}>
        <PolityPage />
        <spy.SearchSpy />
      </MemoryRouter>
    </QueryClientProvider>
  );
  return screen.findByTestId('polity-player');
}

const tickParam = () => new URLSearchParams(spy.search()).get('tick');

describe('TickPlayer', () => {
  beforeEach(() => {
    apiClient.GET.mockReset();
  });
  afterEach(() => vi.useRealTimers());

  it('scrubs and steps through the run, with the ends disabled', async () => {
    await renderPlayer();
    expect(screen.getByTestId('player-step-back')).toBeDisabled();
    expect(screen.getByTestId('player-position')).toHaveTextContent('Year 1 · Q1 — tick 0 of 12');

    fireEvent.change(screen.getByTestId('player-slider'), { target: { value: '9' } });
    await waitFor(() => expect(tickParam()).toBe('9'));
    expect(screen.getByTestId('player-position')).toHaveTextContent('Year 3 · Q2 — tick 9 of 12');
    expect(screen.getByTestId('player-slider')).toHaveAttribute('aria-valuetext', 'Year 3 · Q2');

    fireEvent.click(screen.getByTestId('player-step-back'));
    await waitFor(() => expect(tickParam()).toBe('8'));
    fireEvent.click(screen.getByTestId('player-step-forward'));
    await waitFor(() => expect(tickParam()).toBe('9'));

    fireEvent.change(screen.getByTestId('player-slider'), { target: { value: '12' } });
    await waitFor(() => expect(screen.getByTestId('player-step-forward')).toBeDisabled());
  });

  it('answers the keyboard and ignores keys it does not use', async () => {
    const player = await renderPlayer('/polity?tick=5');
    fireEvent.keyDown(player, { key: 'ArrowRight' });
    await waitFor(() => expect(tickParam()).toBe('6'));
    fireEvent.keyDown(player, { key: 'PageUp' });
    await waitFor(() => expect(tickParam()).toBe('2'));
    fireEvent.keyDown(player, { key: 'End' });
    await waitFor(() => expect(tickParam()).toBe('12'));
    fireEvent.keyDown(player, { key: 'Home' });
    await waitFor(() => expect(tickParam()).toBe('0'));
    fireEvent.keyDown(player, { key: 'q' });
    expect(tickParam()).toBe('0');
    fireEvent.keyDown(player, { key: ' ' });
    expect(screen.getByTestId('player-toggle')).toHaveAttribute('aria-pressed', 'true');
    fireEvent.keyDown(player, { key: ' ' });
    expect(screen.getByTestId('player-toggle')).toHaveAttribute('aria-pressed', 'false');
  });

  it('plays a tick per beat at its speed and stops at the last tick', async () => {
    await renderPlayer('/polity?tick=10');
    vi.useFakeTimers();
    fireEvent.change(screen.getByTestId('player-speed'), { target: { value: '4' } });
    fireEvent.click(screen.getByTestId('player-toggle'));
    expect(screen.getByTestId('player-toggle')).toHaveTextContent('Pause');

    await act(async () => {
      vi.advanceTimersByTime(250);
    });
    expect(tickParam()).toBe('11');
    await act(async () => {
      vi.advanceTimersByTime(500);
    });
    expect(tickParam()).toBe('12');
    await act(async () => {
      vi.advanceTimersByTime(250);
    });
    expect(screen.getByTestId('player-toggle')).toHaveAttribute('aria-pressed', 'false');
    expect(screen.getByTestId('player-toggle')).toHaveTextContent('Play');
  });

  it('rewinds to the start when played from the end', async () => {
    await renderPlayer('/polity?tick=12');
    fireEvent.click(screen.getByTestId('player-toggle'));
    await waitFor(() => expect(tickParam()).toBe('0'));
    fireEvent.click(screen.getByTestId('player-toggle'));
    expect(screen.getByTestId('player-toggle')).toHaveAttribute('aria-pressed', 'false');
  });
});

describe('InstitutionalTimeline', () => {
  beforeEach(() => {
    apiClient.GET.mockReset();
  });

  const story = runOverview('aaaa', {
    terms: [
      {
        holder: 2,
        start_tick: 0,
        end_tick: 9,
        ended_by: 'legitimacy_floor',
        lame_duck: false,
        mandate_strength: 0.6,
      },
      {
        holder: 21,
        start_tick: 10,
        end_tick: 11,
        ended_by: 'confidence_vote',
        lame_duck: false,
        mandate_strength: 0.5,
      },
      {
        holder: 2,
        start_tick: 12,
        end_tick: 12,
        ended_by: 'run_end',
        lame_duck: true,
        mandate_strength: null,
      },
      {
        holder: 7,
        start_tick: 12,
        end_tick: 12,
        ended_by: 'something_else',
        lame_duck: false,
        mandate_strength: null,
      },
    ],
    timeline: [
      { tick: 0, event_type: 'elected', citizen_id: 2, details: {} },
      { tick: 9, event_type: 'recalled', citizen_id: 2, details: {} },
      { tick: 9, event_type: 'snap_election_triggered', citizen_id: null, details: {} },
      { tick: 10, event_type: 'election_no_winner', citizen_id: null, details: {} },
      { tick: 11, event_type: 'petition_launched', citizen_id: 5, details: {} },
      { tick: 11, event_type: 'bill_enacted', citizen_id: null, details: {} },
      { tick: 12, event_type: 'scandal_occurred', citizen_id: 2, details: {} },
      { tick: 12, event_type: 'brand_new_event', citizen_id: null, details: {} },
      { tick: 12, event_type: 'amendment_proposed', citizen_id: 2, details: {} },
      { tick: 12, event_type: 'constitution_amended', citizen_id: null, details: {} },
      // Phase 5: appended last, in lanes empty at tick 12, so no earlier glyph or jump index moves.
      { tick: 12, event_type: 'extra_legal_act', citizen_id: 2, details: {} },
      { tick: 12, event_type: 'campaign_run', citizen_id: 7, details: {} },
    ],
  });

  async function renderTimeline(url = '/polity', overview = story) {
    servePolity(apiClient.GET, { overview });
    render(
      <QueryClientProvider client={makeTestQueryClient()}>
        <MemoryRouter initialEntries={[url]}>
          <PolityPage />
          <spy.SearchSpy />
        </MemoryRouter>
      </QueryClientProvider>
    );
    return screen.findByTestId('timeline-svg');
  }

  it('draws the terms, a shape per event kind and the playhead at the current tick', async () => {
    const svg = await renderTimeline('/polity?tick=6');
    expect(svg).toHaveAttribute('aria-label', '4 terms and 12 institutional events over 13 ticks');
    const terms = screen.getAllByTestId('timeline-term');
    expect(terms).toHaveLength(4);
    expect(terms[0]).toHaveTextContent(
      'Term of citizen 2, from tick 0 (recalled: legitimacy under the floor)'
    );
    expect(terms[1]).toHaveTextContent('confidence vote lost');
    expect(terms[2]).toHaveTextContent('still running when the run ended');
    expect(terms[3]).toHaveTextContent('ended by an election');
    expect(screen.getAllByTestId('timeline-glyph').map((g) => g.getAttribute('data-kind'))).toEqual(
      [
        'elected',
        'recall',
        'snap',
        'noWinner',
        'petition',
        'bill',
        'scandal',
        'other',
        'amendment',
        'amended',
        'extraLegal',
        'campaign',
      ]
    );
    // Each Phase 5 act draws its own shape, not the generic bar 'other' falls back to.
    const shapeOf = (kind: string) =>
      document.querySelector(`[data-testid="timeline-glyph"][data-kind="${kind}"] path`);
    expect(shapeOf('extraLegal')).toHaveClass('fill-red-700');
    expect(shapeOf('campaign')).toHaveClass('stroke-emerald-700');
    const jumps = screen.getAllByTestId('timeline-event-jump');
    expect(jumps.at(-2)).toHaveTextContent('Tick 12: extra-legal act');
    expect(jumps.at(-1)).toHaveTextContent('Tick 12: campaign');
    const x6 = screen.getByTestId('timeline-playhead').getAttribute('x1');
    fireEvent.keyDown(screen.getByTestId('polity-player'), { key: 'End' });
    await waitFor(() =>
      expect(screen.getByTestId('timeline-playhead').getAttribute('x1')).not.toBe(x6)
    );
  });

  it('explains each shape it draws, and only those', async () => {
    const legend = () => screen.getAllByTestId(/^timeline-legend-/).map((e) => e.textContent);
    await renderTimeline();
    expect(screen.getByTestId('timeline-legend')).toHaveAccessibleName('Timeline legend');
    expect(legend()).toEqual([
      'election won',
      'election without a winner, or invalidated',
      'snap election',
      'campaign',
      'president recalled',
      'petition or confidence vote',
      'extra-legal act',
      'legislative election, bill or coalition',
      'constitution amended',
      'amendment or referendum',
      'society event',
    ]);
    cleanup();

    await renderTimeline(
      '/polity',
      runOverview('aaaa', {
        timeline: [
          { tick: 0, event_type: 'elected', citizen_id: 2, details: {} },
          { tick: 3, event_type: 'economic_shock_tick', citizen_id: null, details: {} },
        ],
      })
    );
    expect(legend()).toEqual(['election won', 'society event']);
  });

  it('moves the player to a clicked tick or a listed event', async () => {
    const svg = await renderTimeline();
    vi.spyOn(svg, 'getBoundingClientRect').mockReturnValue({ left: 100 } as DOMRect);
    fireEvent.click(svg, { clientX: 100 + 400 });
    await waitFor(() => expect(tickParam()).toBe('6'));

    const jumps = screen.getAllByTestId('timeline-event-jump');
    expect(jumps[1]).toHaveTextContent('Tick 9: president recalled');
    expect(jumps[7]).toHaveTextContent('Tick 12: brand_new_event');
    fireEvent.click(jumps[1]);
    await waitFor(() => expect(tickParam()).toBe('9'));
  });

  it('fits the width its container reports', async () => {
    const observers: ResizeObserverCallback[] = [];
    const Original = window.ResizeObserver;
    window.ResizeObserver = class {
      constructor(callback: ResizeObserverCallback) {
        observers.push(callback);
      }
      observe() {}
      unobserve() {}
      disconnect() {}
    } as unknown as typeof ResizeObserver;
    try {
      const svg = await renderTimeline();
      expect(svg).toHaveAttribute('width', '800');
      act(() => {
        for (const callback of observers) {
          callback([{ contentRect: { width: 0 } } as ResizeObserverEntry], {} as ResizeObserver);
          callback([{ contentRect: { width: 424 } } as ResizeObserverEntry], {} as ResizeObserver);
        }
      });
      expect(screen.getByTestId('timeline-svg')).toHaveAttribute('width', '424');
    } finally {
      window.ResizeObserver = Original;
    }
  });
});
