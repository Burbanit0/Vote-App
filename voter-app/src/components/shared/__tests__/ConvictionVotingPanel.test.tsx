import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import ConvictionVotingPanel from '../ConvictionVotingPanel';
import { ElectionProvider } from '../../../context/ElectionContext';

jest.mock('axios', () => ({ post: jest.fn() }));
const { post: mockPost } = jest.requireMock('axios') as { post: jest.Mock };

jest.mock('recharts', () => {
  const React = require('react');
  return {
    BarChart:            ({ children }: any) => <div data-testid="compare-bar-chart">{children}</div>,
    Bar:                 () => null,
    Cell:                () => null,
    XAxis:               () => null,
    YAxis:               () => null,
    CartesianGrid:       () => null,
    Tooltip:             () => null,
    Legend:              () => null,
    ResponsiveContainer: ({ children }: any) => <div style={{ width: 400, height: 180 }}>{children}</div>,
  };
});

// ── Fixture ───────────────────────────────────────────────────────────────────

function makeData(winnerChanged = false) {
  return {
    data: {
      conviction_winner: winnerChanged ? 'B' : 'A',
      token_winner:      'A',
      winner_changed:    winnerChanged,
      proposals: [
        { name: 'A', conviction_score: 80000, token_score: 60000,
          avg_conviction_of_supporters: 2.5, avg_tokens_of_supporters: 1200 },
        { name: 'B', conviction_score: winnerChanged ? 90000 : 55000, token_score: 50000,
          avg_conviction_of_supporters: 4.0, avg_tokens_of_supporters: 800 },
        { name: 'C', conviction_score: 30000, token_score: 25000,
          avg_conviction_of_supporters: 1.5, avg_tokens_of_supporters: 900 },
      ],
      voter_scatter: Array.from({ length: 50 }, (_, i) => ({
        id: i, tokens: 500 + i * 20, lock_days: [0, 7, 28, 224][i % 4],
        conviction_mult: [0.1, 1, 3, 6][i % 4], conviction_weight: (500 + i * 20) * [0.1, 1, 3, 6][i % 4],
        choice: ['A', 'B', 'C'][i % 3],
      })),
      voter_stats: {
        gini_tokens:          0.62,
        gini_conviction:      0.45,
        whale_pct_tokens:     0.55,
        whale_pct_conviction: 0.30,
      },
      pedagogical_note: 'Test note.',
      lock_options: [0, 7, 14, 28, 56, 112, 224],
      multipliers:   { '0': 0.1, '7': 1, '14': 2, '28': 3, '56': 4, '112': 5, '224': 6 },
    },
  };
}

function renderPanel() {
  return render(
    <MemoryRouter>
      <ElectionProvider>
        <ConvictionVotingPanel />
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

describe('ConvictionVotingPanel', () => {
  it('shows simulate button', () => {
    renderPanel();
    expect(screen.getByRole('button', { name: /simuler|simulate/i })).toBeInTheDocument();
  });

  it('shows distribution selector', () => {
    renderPanel();
    expect(screen.getByTestId('distribution-select')).toBeInTheDocument();
  });

  it('shows prompt before first run', () => {
    renderPanel();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('calls axios.post on simulate click', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));
    expect(mockPost).toHaveBeenCalledWith(
      expect.stringContaining('/api/election/conviction-voting'),
      expect.any(Object),
    );
    jest.runAllTimers();
  });

  it('renders scatter SVG after data loads', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('conviction-scatter-svg')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows token and conviction winner badges', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByTestId('token-winner-badge')).toBeInTheDocument();
      expect(screen.getByTestId('conviction-winner-badge')).toBeInTheDocument();
    });
    jest.runAllTimers();
  });

  it('shows comparison banner', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('comparison-banner')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows winner-changed alert when winner changed', async () => {
    mockPost.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('winner-changed-alert')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('does not show winner-changed alert when stable', async () => {
    mockPost.mockResolvedValue(makeData(false));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('comparison-banner')).toBeInTheDocument());
    expect(screen.queryByTestId('winner-changed-alert')).not.toBeInTheDocument();
    jest.runAllTimers();
  });

  it('shows Gini token and conviction badges', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByTestId('gini-tokens-badge')).toBeInTheDocument();
      expect(screen.getByTestId('gini-conviction-badge')).toBeInTheDocument();
    });
    jest.runAllTimers();
  });

  it('shows whale dominance badges', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByTestId('whale-tokens-badge')).toBeInTheDocument();
      expect(screen.getByTestId('whale-conviction-badge')).toBeInTheDocument();
    });
    jest.runAllTimers();
  });

  it('renders proposals comparison table', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('proposals-table')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows whale sliders when whale distribution selected', () => {
    renderPanel();
    fireEvent.change(screen.getByTestId('distribution-select'), { target: { value: 'whale' } });
    expect(screen.getByTestId('whale-pct-slider')).toBeInTheDocument();
    expect(screen.getByTestId('small-lock-select')).toBeInTheDocument();
  });

  it('hides whale sliders for non-whale distribution', () => {
    renderPanel();
    fireEvent.change(screen.getByTestId('distribution-select'), { target: { value: 'skewed' } });
    expect(screen.queryByTestId('whale-pct-slider')).not.toBeInTheDocument();
  });

  it('sends correct distribution parameter', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.change(screen.getByTestId('distribution-select'), { target: { value: 'skewed' } });
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));
    const body = mockPost.mock.calls[0][1];
    expect(body.conviction_distribution).toBe('skewed');
    jest.runAllTimers();
  });

  it('gini-conviction badge is green when conviction more equal', async () => {
    // gini_conviction=0.45 < gini_tokens=0.62 → green badge
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      const badge = screen.getByTestId('gini-conviction-badge');
      expect(badge.className).toContain('bg-success');
    });
    jest.runAllTimers();
  });

  it('shows error on API failure', async () => {
    mockPost.mockRejectedValue(new Error('Network error'));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument());
  });
});
