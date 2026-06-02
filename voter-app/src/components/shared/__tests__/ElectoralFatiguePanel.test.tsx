import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import ElectoralFatiguePanel from '../ElectoralFatiguePanel';
import { ElectionProvider } from '../../../stores/useElectionStore';
import { makeTestQueryClient } from '../../../test/queryWrapper';

vi.mock('../../../api/client', () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn(), PATCH: vi.fn() },
  getAccessToken: vi.fn(() => null),
}));
const { apiClient } = (await import('../../../api/client')) as unknown as { apiClient: { POST: jest.Mock } };

vi.mock('recharts', () => {
  const React = require('react');
  return {
    LineChart:           ({ children }: any) => <div>{children}</div>,
    AreaChart:           ({ children }: any) => <div>{children}</div>,
    Line:                ({ dataKey }: any) => <div data-testid={`line-${dataKey}`} />,
    Area:                ({ dataKey }: any) => <div data-testid={`area-${dataKey}`} />,
    XAxis:               () => null,
    YAxis:               () => null,
    CartesianGrid:       () => null,
    Tooltip:             () => null,
    Legend:              () => null,
    ReferenceLine:       () => null,
    ResponsiveContainer: ({ children }: any) => <div style={{ width: 400, height: 200 }}>{children}</div>,
  };
});

// ── Fixture ───────────────────────────────────────────────────────────────────

function makeData(winnerChanged = false) {
  const candidates = ['Alice', 'Bob', 'Carol'];
  return {
    data: {
      elections: Array.from({ length: 6 }, (_, k) => ({
        election_n: k + 1,
        turnout:    Math.max(0.25, 1 - k * 0.07),
        winner:     winnerChanged && k >= 3 ? 'Bob' : 'Alice',
        voter_profile: {
          mean_ideology_x: k * 0.03,
          partisan_pct:    0.2 + k * 0.04,
        },
        vote_shares: { Alice: winnerChanged && k >= 3 ? 0.35 : 0.44, Bob: winnerChanged && k >= 3 ? 0.45 : 0.33, Carol: 0.23 },
      })),
      winner_drift:         Array.from({ length: 6 }, (_, k) => winnerChanged && k >= 3 ? 'Bob' : 'Alice'),
      winner_changed_at:    winnerChanged ? 4 : null,
      ideology_drift:       0.15,
      representation_gap:   0.09,
      full_mean_ideology:   0.03,
      pedagogical_note:     'Test note.',
    },
    error: undefined,
  };
}

function renderPanel() {
  return render(
    <MemoryRouter>
      <QueryClientProvider client={makeTestQueryClient()}>
        <ElectionProvider>
          <ElectoralFatiguePanel />
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

afterEach(() => { vi.useRealTimers(); });

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('ElectoralFatiguePanel', () => {
  it('shows simulate button', () => {
    renderPanel();
    expect(screen.getByRole('button', { name: /simuler|simulate/i })).toBeInTheDocument();
  });

  it('shows fatigue rate slider', () => {
    renderPanel();
    expect(screen.getByTestId('fatigue-rate-slider')).toBeInTheDocument();
  });

  it('shows engaged voters slider', () => {
    renderPanel();
    expect(screen.getByTestId('engaged-slider')).toBeInTheDocument();
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
      expect.stringMatching(/\/api\/(v2\/)?election\/electoral-fatigue/),
      expect.any(Object),
    );
    vi.runAllTimers();
  });

  it('renders turnout chart after data loads', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('turnout-chart')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('renders area chart after data loads', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('area-chart')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows composition bars', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('composition-bars')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows ideology drift badge', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('ideology-drift-badge')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows representation gap badge', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('rep-gap-badge')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows final turnout badge', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('final-turnout-badge')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows winner-changed badge when winner changed', async () => {
    apiClient.POST.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('winner-changed-badge')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('does NOT show winner-changed badge when winner stable', async () => {
    apiClient.POST.mockResolvedValue(makeData(false));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => screen.getByTestId('ideology-drift-badge'));
    expect(screen.queryByTestId('winner-changed-badge')).not.toBeInTheDocument();
    vi.runAllTimers();
  });

  it('shows winner drift badges for each election', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('winner-drift-badges')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('auto-recalculates on fatigue slider change after first run', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));

    fireEvent.change(screen.getByTestId('fatigue-rate-slider'), { target: { value: '0.1' } });
    act(() => { vi.advanceTimersByTime(450); });
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
