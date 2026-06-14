import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import MultiwinnerCompare from '../MultiwinnerCompare';
import { ElectionProvider } from '../../../stores/useElectionStore';
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
  const makeMethod = (seats: Record<string, number>, distortion: number) => ({
    seats,
    elected: Object.entries(seats)
      .filter(([, s]) => s > 0)
      .map(([c]) => c),
    distortion,
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
        fptp: makeMethod({ Alice: 4, Bob: 0, Carol: 0, Dave: 0 }, 0.3),
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

  it('comparison table shows all 5 methods', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /comparer|compare/i }));
    await waitFor(() => {
      expect(screen.getAllByText('STV').length).toBeGreaterThan(0);
      expect(screen.getAllByText("D'Hondt").length).toBeGreaterThan(0);
      expect(screen.getAllByText('SPAV').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Phragmén').length).toBeGreaterThan(0);
      expect(screen.getAllByText('FPTP').length).toBeGreaterThan(0);
    });
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
