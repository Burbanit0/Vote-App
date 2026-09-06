import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import AdaptiveVotingPanel from '../AdaptiveVotingPanel';
import { ElectionProvider } from '../../../stores/useElectionStore';
import { makeTestQueryClient } from '../../../test/queryWrapper';

vi.mock('../../../api/client', () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn(), PATCH: vi.fn() },
}));
const { apiClient } = (await import('../../../api/client')) as unknown as {
  apiClient: { POST: jest.Mock };
};

vi.mock('recharts', () => {
  const React = require('react');
  return {
    LineChart: ({ children }: any) => <div data-testid="line-chart">{children}</div>,
    Line: () => null,
    XAxis: () => null,
    YAxis: () => null,
    Tooltip: () => null,
    Legend: () => null,
    ReferenceLine: () => null,
    ResponsiveContainer: ({ children }: any) => (
      <div style={{ width: 400, height: 300 }}>{children}</div>
    ),
  };
});

const makeRound = (rnd: number, winner: string, tacticalPct = 0): any => ({
  round: rnd,
  vote_shares: { Alice: 0.45, Bob: 0.35, Carol: 0.2 },
  sincere_shares: { Alice: 0.4, Bob: 0.38, Carol: 0.22 },
  winner,
  sincere_winner: 'Alice',
  strategic_voters_pct: tacticalPct,
  voter_snapshot: [
    { id: 0, x: -0.3, y: 0.1, sincere_vote: 'Carol', effective_vote: 'Alice', tactical: true },
    { id: 1, x: 0.4, y: -0.1, sincere_vote: 'Bob', effective_vote: 'Bob', tactical: false },
  ],
});

const makeData = (winnerChanged = false) => ({
  data: {
    rounds: [
      makeRound(0, 'Alice', 0),
      makeRound(1, winnerChanged ? 'Bob' : 'Alice', 0.12),
      makeRound(2, winnerChanged ? 'Bob' : 'Alice', 0.15),
      makeRound(3, winnerChanged ? 'Bob' : 'Alice', 0.14),
    ],
    converged: true,
    convergence_round: 2,
    final_winner: winnerChanged ? 'Bob' : 'Alice',
    sincere_winner: 'Alice',
    strategic_drift: winnerChanged ? 0.22 : 0.0,
    candidates: [
      { name: 'Alice', x: -0.5 },
      { name: 'Bob', x: 0.5 },
      { name: 'Carol', x: 0.0 },
    ],
  },
  error: undefined,
});

function renderPanel() {
  return render(
    <MemoryRouter>
      <QueryClientProvider client={makeTestQueryClient()}>
        <ElectionProvider>
          <AdaptiveVotingPanel />
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

describe('AdaptiveVotingPanel', () => {
  it('shows simulate button', () => {
    renderPanel();
    expect(screen.getByRole('button', { name: /simuler|simulate/i })).toBeInTheDocument();
  });

  it('shows prompt before running', () => {
    renderPanel();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('calls API on button click', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));
    expect(apiClient.POST).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/(v2\/)?election\/adaptive/),
      expect.any(Object)
    );
  });

  it('renders LineChart after data loads', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByTestId('race-chart')).toBeInTheDocument();
    });
    act(() => {
      vi.runAllTimers();
    });
  });

  it('shows convergence badge', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByTestId('convergence-badge')).toBeInTheDocument();
    });
    act(() => {
      vi.runAllTimers();
    });
  });

  it('shows final winner badge', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByTestId('final-winner-badge')).toBeInTheDocument();
    });
    act(() => {
      vi.runAllTimers();
    });
  });

  it('shows sincere winner badge', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByTestId('sincere-winner-badge')).toBeInTheDocument();
    });
    act(() => {
      vi.runAllTimers();
    });
  });

  it('shows drift badge when winner changed and drift > 0.15', async () => {
    apiClient.POST.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByTestId('drift-badge')).toBeInTheDocument();
    });
    act(() => {
      vi.runAllTimers();
    });
  });

  it('renders ideology overlay SVG', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByTestId('ideology-overlay')).toBeInTheDocument();
    });
    act(() => {
      vi.runAllTimers();
    });
  });

  it('shows warning alert when tacticals changed the winner', async () => {
    apiClient.POST.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      const warnings = document.querySelectorAll('.bg-amber-100');
      expect(warnings.length).toBeGreaterThan(0);
    });
    act(() => {
      vi.runAllTimers();
    });
  });

  it('shows replay button after data loads', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /replay|rejouer/i })).toBeInTheDocument();
    });
    act(() => {
      vi.runAllTimers();
    });
  });

  it('shows error on API failure', async () => {
    apiClient.POST.mockRejectedValue(new Error('Network'));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument();
    });
  });
});
