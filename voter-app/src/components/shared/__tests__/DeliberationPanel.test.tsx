import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import DeliberationPanel from '../DeliberationPanel';
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
    Line:                ({ dataKey }: any) => <div data-testid={`line-${dataKey}`} />,
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

function makeData(winnerChanged = false, polarPos = false) {
  return {
    data: {
      pre_deliberation: {
        winner:           'Alice',
        vote_shares:      { Alice: 0.44, Bob: 0.33, Carol: 0.23 },
        condorcet_winner: 'Alice',
        mean_regret:      0.18,
        ideology_variance: 0.32,
      },
      post_deliberation: {
        winner:           winnerChanged ? 'Carol' : 'Alice',
        vote_shares:      { Alice: winnerChanged ? 0.35 : 0.42, Bob: 0.30, Carol: winnerChanged ? 0.35 : 0.28 },
        condorcet_winner: 'Carol',
        mean_regret:      0.12,
        ideology_variance: polarPos ? 0.45 : 0.20,
      },
      winner_changed: winnerChanged,
      deliberation_effect: {
        opinion_shift_mean:  0.08,
        convergence_rate:    0.38,
        polarization_change: polarPos ? 0.13 : -0.12,
        regret_improvement:  33.3,
      },
      per_round: Array.from({ length: 5 }, (_, i) => ({
        round:              i + 1,
        variance:           0.32 - i * 0.025,
        mean_position:      -0.01 + i * 0.005,
        winner_if_voted_now: 'Alice',
      })),
      network_effect:   'Test network effect.',
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
          <DeliberationPanel />
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

describe('DeliberationPanel', () => {
  it('shows simulate button', () => {
    renderPanel();
    expect(screen.getByTestId('simulate-btn')).toBeInTheDocument();
  });

  it('shows four network buttons', () => {
    renderPanel();
    expect(screen.getByTestId('network-complete')).toBeInTheDocument();
    expect(screen.getByTestId('network-bridge')).toBeInTheDocument();
    expect(screen.getByTestId('network-random')).toBeInTheDocument();
    expect(screen.getByTestId('network-echo_chamber')).toBeInTheDocument();
  });

  it('shows rounds slider', () => {
    renderPanel();
    expect(screen.getByTestId('rounds-slider')).toBeInTheDocument();
  });

  it('shows influence slider', () => {
    renderPanel();
    expect(screen.getByTestId('influence-slider')).toBeInTheDocument();
  });

  it('shows argument quality slider', () => {
    renderPanel();
    expect(screen.getByTestId('arg-quality-slider')).toBeInTheDocument();
  });

  it('shows prompt before first run', () => {
    renderPanel();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('calls API on simulate click', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));
    expect(apiClient.POST).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/(v2\/)?election\/deliberation/),
      expect.any(Object),
    );
    vi.runAllTimers();
  });

  it('shows pre and post winner badges after data loads', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => {
      expect(screen.getByTestId('pre-winner-badge')).toBeInTheDocument();
      expect(screen.getByTestId('post-winner-badge')).toBeInTheDocument();
    });
    vi.runAllTimers();
  });

  it('shows comparison banner', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('comparison-banner')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows winner-changed alert when winner changed', async () => {
    apiClient.POST.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('winner-changed-alert')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('does NOT show winner-changed alert when winner stable', async () => {
    apiClient.POST.mockResolvedValue(makeData(false));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => screen.getByTestId('comparison-banner'));
    expect(screen.queryByTestId('winner-changed-alert')).not.toBeInTheDocument();
    vi.runAllTimers();
  });

  it('shows effect badges', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => {
      expect(screen.getByTestId('effect-badges')).toBeInTheDocument();
      expect(screen.getByTestId('polarization-badge')).toBeInTheDocument();
      expect(screen.getByTestId('regret-badge')).toBeInTheDocument();
      expect(screen.getByTestId('convergence-badge')).toBeInTheDocument();
    });
    vi.runAllTimers();
  });

  it('polarization badge is red when positive', async () => {
    apiClient.POST.mockResolvedValue(makeData(false, true));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => {
      const badge = screen.getByTestId('polarization-badge');
      expect(badge.className).toContain('bg-[#dc3545]');
    });
    vi.runAllTimers();
  });

  it('renders evolution chart', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('evolution-chart')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows network effect alert', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('network-effect-alert')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('network button changes selection', () => {
    renderPanel();
    fireEvent.click(screen.getByTestId('network-echo_chamber'));
    expect(screen.getByTestId('network-echo_chamber').className).toContain('text-primary-foreground');
    expect(screen.getByTestId('network-random').className).not.toContain('text-primary-foreground');
  });

  it('shows error on API failure', async () => {
    apiClient.POST.mockRejectedValue(new Error('Network error'));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument());
  });
});
