import React from 'react';
import type { Mock } from 'vitest';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
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
const param = (name: string) => new URLSearchParams(spy.search()).get(name);

// Four citizens at the corners of a unit square, two parties, citizen 2 president.
const overview = (overrides: Record<string, unknown> = {}) =>
  runOverview('aaaa', {
    population: 4,
    projection: {
      method: 'latent',
      positions: 'static',
      axes: [
        [
          { issue: 4, weight: 0.9 },
          { issue: 0, weight: -0.5 },
        ],
        [{ issue: 11, weight: 0.8 }],
      ],
      citizens: [
        {
          year: 0,
          xy: [
            [0, 0],
            [1, 0],
            [0, 1],
            [1, 1],
          ],
        },
      ],
    },
    parties: [
      { party_id: 0, xy: [0.25, 0.5] },
      { party_id: 1, xy: [0.75, 0.5] },
    ],
    citizen_parties: [0, 1, 0, null],
    ...overrides,
  });

const frame = (tick: number) => ({
  tick,
  partial: false,
  status: [0, 1, 2, 0],
  chamber: [0, 0, 0, 1],
  act: [3, -1, -1, 1],
  vote: [1, 2, 0, -1],
  candidacy: [-1, 3, 4, 0],
  president: {
    citizen_id: 2,
    xy: [0.1, 0.9],
    pledged_xy: tick > 0 ? [0, 1] : null,
    legitimacy: 0.4,
    ecart: 0.05,
    mandate_strength: 0.6,
    lame_duck: false,
  },
});

const drawn: string[] = [];
beforeAll(() => {
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockImplementation(
    () =>
      new Proxy(
        {},
        {
          get: (_target, name) =>
            name === 'fillStyle' || name === 'strokeStyle' || name === 'lineWidth'
              ? ''
              : (...args: unknown[]) => drawn.push(`${String(name)}(${args.join(',')})`),
          set: () => true,
        }
      ) as unknown as CanvasRenderingContext2D
  );
});

async function renderMap(url = '/polity', responses: Parameters<typeof servePolity>[1] = {}) {
  servePolity(apiClient.GET, { overview: overview(), frame, ...responses });
  render(
    <QueryClientProvider client={makeTestQueryClient()}>
      <MemoryRouter initialEntries={[url]}>
        <PolityPage />
        <spy.SearchSpy />
      </MemoryRouter>
    </QueryClientProvider>
  );
  return screen.findByTestId('polity-map-surface');
}

describe('PopulationMap', () => {
  beforeEach(() => {
    apiClient.GET.mockReset();
    drawn.length = 0;
  });

  it('draws every citizen on the canvas and lays the story over it', async () => {
    await renderMap('/polity?tick=3');
    expect(screen.getByTestId('polity-map-canvas')).toHaveAttribute(
      'aria-label',
      'Tick 3, 4 citizens: elector 1, candidate 1, president 1, seat in the sortition chamber 1'
    );
    await waitFor(() => expect(drawn.filter((c) => c === 'beginPath()')).toHaveLength(4));
    expect(drawn[0]).toMatch(/^setTransform\(/);
    expect(screen.getAllByTestId('polity-map-party')).toHaveLength(2);
    expect(screen.getByTestId('polity-map-president')).toHaveTextContent('President: citizen 2');
    expect(screen.getByTestId('polity-map-drift')).toBeInTheDocument();
    const overlay = screen.getByTestId('polity-map-overlay');
    expect(overlay).toHaveTextContent('Latent axis 1 — issues: no. 5, no. 1');
    expect(overlay).toHaveTextContent('Latent axis 2 — issues: no. 12');
  });

  it('switches lenses from the selector, with notes where the reading is partial', async () => {
    await renderMap('/polity', { overview: overview({ vote_coverage: 'audit_sample' }) });
    expect(screen.queryByTestId('polity-map-drift')).not.toBeInTheDocument(); // no pledge at tick 0
    expect(screen.getByTestId('polity-lens-activity')).toHaveAttribute('aria-checked', 'true');

    fireEvent.click(screen.getByTestId('polity-lens-vote'));
    await waitFor(() => expect(param('lens')).toBe('vote'));
    expect(screen.getByTestId('polity-map-vote-note')).toHaveTextContent('Only the audit sample');
    expect(
      within(screen.getByTestId('polity-map-legend')).getByText('for the winner')
    ).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('polity-lens-act'));
    await waitFor(() =>
      expect(screen.getByTestId('polity-legend-mobilize')).toHaveTextContent('mobilizes1')
    );
    expect(screen.queryByTestId('polity-map-vote-note')).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId('polity-lens-candidacy'));
    await waitFor(() =>
      expect(screen.getByTestId('polity-legend-electedCandidate')).toBeInTheDocument()
    );

    fireEvent.click(screen.getByTestId('polity-lens-party'));
    await waitFor(() =>
      expect(screen.getByTestId('polity-legend-party0')).toHaveTextContent('party 02')
    );
    expect(screen.getByTestId('polity-legend-noParty')).toHaveTextContent('no party1');
  });

  it('says when the run journals no ballot and when positions move yearly', async () => {
    await renderMap('/polity?lens=vote', {
      overview: overview({
        vote_coverage: 'none',
        projection: {
          method: 'pca',
          positions: 'yearly',
          axes: [[{ issue: 0, weight: 1 }], [{ issue: 1, weight: 1 }]],
          citizens: [
            {
              year: 0,
              xy: [
                [0, 0],
                [1, 0],
                [0, 1],
                [1, 1],
              ],
            },
          ],
        },
      }),
    });
    expect(screen.getByTestId('polity-map-vote-note')).toHaveTextContent(
      'This run journals no ballot.'
    );
    expect(screen.getByTestId('polity-map-yearly-note')).toBeInTheDocument();
    expect(screen.getByTestId('polity-map-overlay')).toHaveTextContent('Principal component 1');
  });

  it('selects a citizen by click, by arrows and from the table, and clears with Escape', async () => {
    const surface = await renderMap();
    vi.spyOn(surface, 'getBoundingClientRect').mockReturnValue({ left: 0, top: 0 } as DOMRect);
    fireEvent.click(surface, { clientX: 5, clientY: 5 });
    await waitFor(() => expect(param('citizen')).toBeNull());

    // Citizen 2 sits at map (0, 1): top-left corner of the scene.
    const scene = {
      width: Number(surface.style.width.replace('px', '')),
      height: Number(surface.style.height.replace('px', '')),
    };
    expect(scene.width).toBe(640);
    fireEvent.keyDown(surface, { key: 'ArrowUp' });
    await waitFor(() => expect(param('citizen')).not.toBeNull());
    expect(screen.getByTestId('polity-map-selection')).toBeInTheDocument();
    const first = param('citizen');
    fireEvent.keyDown(surface, { key: 'ArrowRight' });
    fireEvent.keyDown(surface, { key: 'ArrowRight' });
    fireEvent.keyDown(surface, { key: 'Enter' });
    await waitFor(() => expect(param('citizen')).not.toBe(first));

    fireEvent.keyDown(surface, { key: 'Escape' });
    await waitFor(() => expect(param('citizen')).toBeNull());
    expect(screen.queryByTestId('polity-map-selection')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Select citizen 3' }));
    await waitFor(() => expect(param('citizen')).toBe('3'));
    expect(screen.getByTestId('polity-row-3')).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByTestId('polity-map-selected')).toHaveTextContent('Citizen 3 selected');
    expect(
      within(screen.getByTestId('polity-row-3')).getByText('seat in the sortition chamber')
    ).toBeInTheDocument();
    expect(within(screen.getByTestId('polity-row-3')).getByText('—')).toBeInTheDocument();
  });

  it('hits the citizen under a click', async () => {
    const surface = await renderMap('/polity');
    vi.spyOn(surface, 'getBoundingClientRect').mockReturnValue({ left: 10, top: 20 } as DOMRect);
    // Citizen 1 is at map (1, 0): the bottom-right corner of the fitted square.
    const height = Number(surface.style.height.replace('px', ''));
    const right = 640 / 2 + (height - 48) / 2;
    fireEvent.click(surface, { clientX: 10 + right, clientY: 20 + height - 24 });
    await waitFor(() => expect(param('citizen')).toBe('1'));
  });

  it('waits for the tick before drawing', async () => {
    servePolity(apiClient.GET, { overview: overview(), frame });
    const served = apiClient.GET.getMockImplementation()!;
    apiClient.GET.mockImplementation((path: string, init: unknown) =>
      path.endsWith('/frames') ? new Promise(() => {}) : served(path, init)
    );
    render(
      <QueryClientProvider client={makeTestQueryClient()}>
        <MemoryRouter initialEntries={['/polity']}>
          <PolityPage />
        </MemoryRouter>
      </QueryClientProvider>
    );
    expect(await screen.findByTestId('polity-map-loading')).toHaveTextContent('Loading the tick');
  });

  it('follows its container width once the tick has loaded', async () => {
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
      const surface = await renderMap();
      act(() => {
        for (const callback of observers) {
          callback([{ contentRect: { width: 0 } } as ResizeObserverEntry], {} as ResizeObserver);
          callback([{ contentRect: { width: 1000 } } as ResizeObserverEntry], {} as ResizeObserver);
        }
      });
      await waitFor(() => expect(surface.style.width).toBe('1000px'));
      expect(surface.style.height).toBe('560px');
    } finally {
      window.ResizeObserver = Original;
    }
  });
});
