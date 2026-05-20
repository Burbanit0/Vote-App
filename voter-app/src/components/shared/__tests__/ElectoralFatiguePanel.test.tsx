import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import ElectoralFatiguePanel from '../ElectoralFatiguePanel';
import { ElectionProvider } from '../../../context/ElectionContext';

jest.mock('axios', () => ({ post: jest.fn() }));
const { post: mockPost } = jest.requireMock('axios') as { post: jest.Mock };

jest.mock('recharts', () => {
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
  };
}

function renderPanel() {
  return render(
    <MemoryRouter>
      <ElectionProvider>
        <ElectoralFatiguePanel />
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

  it('calls axios.post on simulate click', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));
    expect(mockPost).toHaveBeenCalledWith(
      expect.stringContaining('/api/election/electoral-fatigue'),
      expect.any(Object),
    );
    jest.runAllTimers();
  });

  it('renders turnout chart after data loads', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('turnout-chart')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('renders area chart after data loads', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('area-chart')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows composition bars', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('composition-bars')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows ideology drift badge', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('ideology-drift-badge')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows representation gap badge', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('rep-gap-badge')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows final turnout badge', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('final-turnout-badge')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows winner-changed badge when winner changed', async () => {
    mockPost.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('winner-changed-badge')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('does NOT show winner-changed badge when winner stable', async () => {
    mockPost.mockResolvedValue(makeData(false));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => screen.getByTestId('ideology-drift-badge'));
    expect(screen.queryByTestId('winner-changed-badge')).not.toBeInTheDocument();
    jest.runAllTimers();
  });

  it('shows winner drift badges for each election', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('winner-drift-badges')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('auto-recalculates on fatigue slider change after first run', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));

    fireEvent.change(screen.getByTestId('fatigue-rate-slider'), { target: { value: '0.1' } });
    act(() => { jest.advanceTimersByTime(450); });
    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(2));
    jest.runAllTimers();
  });

  it('shows error on API failure', async () => {
    mockPost.mockRejectedValue(new Error('Network error'));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument());
  });
});
