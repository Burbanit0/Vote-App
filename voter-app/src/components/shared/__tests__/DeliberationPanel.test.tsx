import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import DeliberationPanel from '../DeliberationPanel';
import { ElectionProvider } from '../../../context/ElectionContext';

jest.mock('axios', () => ({ post: jest.fn() }));
const { post: mockPost } = jest.requireMock('axios') as { post: jest.Mock };

jest.mock('recharts', () => {
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
  };
}

function renderPanel() {
  return render(
    <MemoryRouter>
      <ElectionProvider>
        <DeliberationPanel />
      </ElectionProvider>
    </MemoryRouter>
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
  jest.useFakeTimers();
});

afterEach(() => { jest.useRealTimers(); });

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

  it('calls axios.post on simulate click', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));
    expect(mockPost).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/(v2\/)?election\/deliberation/),
      expect.any(Object),
    );
    jest.runAllTimers();
  });

  it('shows pre and post winner badges after data loads', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => {
      expect(screen.getByTestId('pre-winner-badge')).toBeInTheDocument();
      expect(screen.getByTestId('post-winner-badge')).toBeInTheDocument();
    });
    jest.runAllTimers();
  });

  it('shows comparison banner', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('comparison-banner')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows winner-changed alert when winner changed', async () => {
    mockPost.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('winner-changed-alert')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('does NOT show winner-changed alert when winner stable', async () => {
    mockPost.mockResolvedValue(makeData(false));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => screen.getByTestId('comparison-banner'));
    expect(screen.queryByTestId('winner-changed-alert')).not.toBeInTheDocument();
    jest.runAllTimers();
  });

  it('shows effect badges', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => {
      expect(screen.getByTestId('effect-badges')).toBeInTheDocument();
      expect(screen.getByTestId('polarization-badge')).toBeInTheDocument();
      expect(screen.getByTestId('regret-badge')).toBeInTheDocument();
      expect(screen.getByTestId('convergence-badge')).toBeInTheDocument();
    });
    jest.runAllTimers();
  });

  it('polarization badge is red when positive', async () => {
    mockPost.mockResolvedValue(makeData(false, true));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => {
      const badge = screen.getByTestId('polarization-badge');
      expect(badge.className).toContain('bg-danger');
    });
    jest.runAllTimers();
  });

  it('renders evolution chart', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('evolution-chart')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows network effect alert', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('network-effect-alert')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('network button changes selection', () => {
    renderPanel();
    fireEvent.click(screen.getByTestId('network-echo_chamber'));
    expect(screen.getByTestId('network-echo_chamber').className).toContain('btn-primary');
    expect(screen.getByTestId('network-random').className).not.toContain('btn-primary');
  });

  it('shows error on API failure', async () => {
    mockPost.mockRejectedValue(new Error('Network error'));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument());
  });
});
