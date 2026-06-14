import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import CompulsoryVotingPanel from '../CompulsoryVotingPanel';
import { ElectionProvider } from '../../../stores/useElectionStore';
import { makeTestQueryClient } from '../../../test/queryWrapper';

vi.mock('../../../api/client', () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn(), PATCH: vi.fn() },
  getAccessToken: vi.fn(() => null),
}));
const { apiClient } = (await import('../../../api/client')) as unknown as {
  apiClient: { POST: jest.Mock };
};

vi.mock('recharts', () => {
  const React = require('react');
  return {
    BarChart: ({ children }: any) => <div>{children}</div>,
    Bar: () => null,
    Cell: () => null,
    XAxis: () => null,
    YAxis: () => null,
    CartesianGrid: () => null,
    Tooltip: () => null,
    Legend: () => null,
    ResponsiveContainer: ({ children }: any) => (
      <div style={{ width: 400, height: 100 }}>{children}</div>
    ),
  };
});

// ── Fixture ───────────────────────────────────────────────────────────────────

function makeData(winnerChanged = false) {
  return {
    data: {
      voluntary: {
        turnout: 0.65,
        winner: 'Alice',
        vote_shares: { Alice: 0.44, Bob: 0.33, Carol: 0.23 },
        null_rate: 0.0,
        voter_profile: { mean_ideology_x: 0.08, partisan_pct: 0.45 },
      },
      compulsory: {
        turnout: 0.92,
        winner: winnerChanged ? 'Bob' : 'Alice',
        vote_shares: {
          Alice: winnerChanged ? 0.35 : 0.42,
          Bob: winnerChanged ? 0.43 : 0.35,
          Carol: 0.23,
        },
        null_rate: 0.035,
        reluctant_count: 81,
        noise_effect: 0.04,
      },
      winner_changed: winnerChanged,
      representation_improvement: 0.06,
      quality_degradation: 0.04,
      pedagogical_note: 'Test note.',
    },
    error: undefined,
  };
}

function renderPanel() {
  return render(
    <MemoryRouter>
      <QueryClientProvider client={makeTestQueryClient()}>
        <ElectionProvider>
          <CompulsoryVotingPanel />
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

describe('CompulsoryVotingPanel', () => {
  it('shows simulate button', () => {
    renderPanel();
    expect(screen.getByRole('button', { name: /simuler|simulate/i })).toBeInTheDocument();
  });

  it('shows all four sliders', () => {
    renderPanel();
    expect(screen.getByTestId('vol-turnout-slider')).toBeInTheDocument();
    expect(screen.getByTestId('comp-turnout-slider')).toBeInTheDocument();
    expect(screen.getByTestId('null-rate-slider')).toBeInTheDocument();
    expect(screen.getByTestId('random-pct-slider')).toBeInTheDocument();
  });

  it('shows examples sidebar', () => {
    renderPanel();
    expect(screen.getByTestId('examples-sidebar')).toBeInTheDocument();
  });

  it('shows prompt before first run', () => {
    renderPanel();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('calls API on simulate click', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));
    expect(apiClient.POST).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/(v2\/)?election\/compulsory-voting/),
      expect.any(Object)
    );
    vi.runAllTimers();
  });

  it('shows voluntary and compulsory result cards', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByTestId('voluntary-card')).toBeInTheDocument();
      expect(screen.getByTestId('compulsory-card')).toBeInTheDocument();
    });
    vi.runAllTimers();
  });

  it('shows metrics row with representation and quality badges', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByTestId('metrics-row')).toBeInTheDocument();
      expect(screen.getByTestId('representation-badge')).toBeInTheDocument();
      expect(screen.getByTestId('quality-badge')).toBeInTheDocument();
    });
    vi.runAllTimers();
  });

  it('shows reluctant badge', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('reluctant-badge')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows winner-changed alert when winner changed', async () => {
    apiClient.POST.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('winner-changed-alert')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('does NOT show winner-changed alert when winner stable', async () => {
    apiClient.POST.mockResolvedValue(makeData(false));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => screen.getByTestId('voluntary-card'));
    expect(screen.queryByTestId('winner-changed-alert')).not.toBeInTheDocument();
    vi.runAllTimers();
  });

  it('debounced re-simulation on vol-turnout slider change', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));

    fireEvent.change(screen.getByTestId('vol-turnout-slider'), { target: { value: '0.55' } });
    act(() => {
      vi.advanceTimersByTime(450);
    });
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(2));
    vi.runAllTimers();
  });

  it('debounced re-simulation on random-pct slider', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));

    fireEvent.change(screen.getByTestId('random-pct-slider'), { target: { value: '0.25' } });
    act(() => {
      vi.advanceTimersByTime(450);
    });
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(2));
    vi.runAllTimers();
  });

  it('shows error on API failure', async () => {
    apiClient.POST.mockRejectedValue(new Error('Network error'));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument());
  });
});
