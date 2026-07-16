import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import MultiwinnerCompare from '../MultiwinnerCompare';
import { ElectionProvider, DEFAULT_CONFIG } from '../../../stores/useElectionStore';
import { makeTestQueryClient } from '../../../test/queryWrapper';

vi.mock('../../../api/client', () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn(), PATCH: vi.fn() },
  getAccessToken: vi.fn(() => null),
}));
const { apiClient } = (await import('../../../api/client')) as unknown as {
  apiClient: { POST: jest.Mock };
};

// ── Fixture ───────────────────────────────────────────────────────────────────

const NAMES = ['Alice', 'Bob', 'Carol', 'Dave'];

function makeData() {
  const jrAll = { jr: true, pjr: true, ejr: true };
  const makeMethod = (seats: Record<string, number>, distortion: number, jr = jrAll) => ({
    seats,
    elected: Object.entries(seats)
      .filter(([, s]) => s > 0)
      .map(([c]) => c),
    distortion,
    justified_representation: jr,
    seat_vs_votes: Object.fromEntries(
      NAMES.map((n) => [
        n,
        {
          seats: seats[n] ?? 0,
          seat_pct: (seats[n] ?? 0) / 4,
          vote_pct: 0.25,
          delta: (seats[n] ?? 0) / 4 - 0.25,
        },
      ])
    ),
  });
  return {
    data: {
      candidates: NAMES,
      num_seats: 4,
      vote_shares: { Alice: 0.4, Bob: 0.3, Carol: 0.2, Dave: 0.1 },
      proportional_reference: { Alice: 2, Bob: 1, Carol: 1, Dave: 0 },
      best_method: 'spav',
      worst_method: 'fptp',
      methods: {
        stv: makeMethod({ Alice: 2, Bob: 1, Carol: 1, Dave: 0 }, 0.04),
        dhondt: makeMethod({ Alice: 2, Bob: 2, Carol: 0, Dave: 0 }, 0.1),
        spav: makeMethod({ Alice: 2, Bob: 1, Carol: 1, Dave: 0 }, 0.04),
        phragmen: makeMethod({ Alice: 2, Bob: 1, Carol: 1, Dave: 0 }, 0.04),
        equal_shares: makeMethod({ Alice: 2, Bob: 1, Carol: 1, Dave: 0 }, 0.04),
        // FPTP elects only Alice — fails justified representation.
        fptp: makeMethod({ Alice: 4, Bob: 0, Carol: 0, Dave: 0 }, 0.3, {
          jr: false,
          pjr: false,
          ejr: false,
        }),
      },
    },
    error: undefined,
  };
}

function renderPanel() {
  return render(
    <MemoryRouter>
      <QueryClientProvider client={makeTestQueryClient()}>
        <ElectionProvider>
          <MultiwinnerCompare />
        </ElectionProvider>
      </QueryClientProvider>
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('MultiwinnerCompare', () => {
  it('shows compare button', () => {
    renderPanel();
    expect(screen.getByRole('button', { name: /comparer|compare/i })).toBeInTheDocument();
  });

  it('shows prompt before running', () => {
    renderPanel();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('calls API on compare click', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /comparer|compare/i }));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));
    expect(apiClient.POST).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/(v2\/)?election\/multiwinner_compare/),
      expect.any(Object)
    );
    vi.runAllTimers();
  });

  it('renders 5 hémicycles after data loads', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    const { container } = renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /comparer|compare/i }));
    await waitFor(() => {
      const svgs = container.querySelectorAll('svg');
      expect(svgs.length).toBeGreaterThanOrEqual(5);
    });
    vi.runAllTimers();
  });

  it('shows distortion badges for each method', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /comparer|compare/i }));
    await waitFor(() => {
      expect(screen.getByTestId('distortion-badge-STV')).toBeInTheDocument();
      expect(screen.getByTestId('distortion-badge-FPTP')).toBeInTheDocument();
    });
    vi.runAllTimers();
  });

  it('shows pedagogical note', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /comparer|compare/i }));
    await waitFor(() => {
      expect(screen.getByTestId('multiwinner-pedagogical')).toBeInTheDocument();
    });
    vi.runAllTimers();
  });

  it('comparison table shows all methods including Method of Equal Shares', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /comparer|compare/i }));
    await waitFor(() => {
      expect(screen.getAllByText('STV').length).toBeGreaterThan(0);
      expect(screen.getAllByText("D'Hondt").length).toBeGreaterThan(0);
      expect(screen.getAllByText('SPAV').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Phragmén').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Parts égales').length).toBeGreaterThan(0);
      expect(screen.getAllByText('FPTP').length).toBeGreaterThan(0);
    });
    vi.runAllTimers();
  });

  it('shows justified-representation badges (EJR for MES, none for FPTP)', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /comparer|compare/i }));
    await waitFor(() => {
      expect(screen.getByTestId('jr-note')).toBeInTheDocument();
      expect(screen.getByTestId('jr-badge-Parts égales')).toHaveTextContent('EJR');
      expect(screen.getByTestId('jr-badge-FPTP')).toHaveTextContent('aucun');
    });
    vi.runAllTimers();
  });

  it('never asks for more seats than the API allows (num_seats < candidates)', async () => {
    // Regression: the API rejects num_seats >= number of candidates. The slider's
    // max already respected that, but the initial state (4) did not — so on the
    // default 3-candidate electorate the very first "Compare" returned 400 and the
    // panel showed "Erreur lors de la simulation", making Method of Equal Shares
    // and the JR readout unreachable out of the box. A mocked API always succeeds,
    // so assert the REQUEST honours the constraint rather than the response.
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    const n = DEFAULT_CONFIG.candidates.length; // 3 — the default electorate
    fireEvent.click(screen.getByRole('button', { name: /comparer|compare/i }));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));
    const body = (apiClient.POST.mock.calls[0][1] as { body: { num_seats: number } }).body;
    expect(body.num_seats).toBeLessThan(n);
    // …and the label agrees with what was sent.
    expect(screen.getByTestId('mw-seats')).toHaveTextContent(String(body.num_seats));
    vi.runAllTimers();
  });

  it('shows error on API failure', async () => {
    apiClient.POST.mockRejectedValue(new Error('Network error'));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /comparer|compare/i }));
    await waitFor(() => expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument());
  });

  it('best method badge is visible', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /comparer|compare/i }));
    await waitFor(() => {
      const bestBadge = screen.getAllByText(/proportionnel|PR/i);
      expect(bestBadge.length).toBeGreaterThan(0);
    });
    vi.runAllTimers();
  });
});
