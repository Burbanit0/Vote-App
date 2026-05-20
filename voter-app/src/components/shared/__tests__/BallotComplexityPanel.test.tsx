import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import BallotComplexityPanel from '../BallotComplexityPanel';
import { ElectionProvider } from '../../../context/ElectionContext';

jest.mock('axios', () => ({ post: jest.fn() }));
const { post: mockPost } = jest.requireMock('axios') as { post: jest.Mock };

jest.mock('recharts', () => {
  const React = require('react');
  return {
    BarChart:            ({ children }: any) => <div>{children}</div>,
    Bar:                 () => null,
    Cell:                () => null,
    LineChart:           ({ children }: any) => <div>{children}</div>,
    Line:                ({ dataKey }: any) => <div data-testid={`line-${dataKey}`} />,
    XAxis:               () => null,
    YAxis:               () => null,
    CartesianGrid:       () => null,
    Tooltip:             () => null,
    Legend:              () => null,
    ResponsiveContainer: ({ children }: any) => <div style={{ width: 400, height: 220 }}>{children}</div>,
  };
});

// ── Fixture ───────────────────────────────────────────────────────────────────

const METHODS = ['plurality', 'approval', 'irv', 'borda', 'star_voting', 'majority_judgment', 'schulze'];

function makeData(winnerChanged = false) {
  return {
    data: {
      results: METHODS.map((m, i) => ({
        method:           m,
        null_rate:        0.01 + i * 0.007,
        blank_rate:       0.03,
        effective_voters: 100 - Math.round((0.01 + i * 0.007) * 100),
        winner:           'Alice',
        winner_changed:   winnerChanged && m === 'schulze',
      })),
      candidate_count_curve: Array.from({ length: 9 }, (_, i) => ({
        n_candidates: i + 2,
        null_rate_by_method: Object.fromEntries(
          METHODS.map((m, j) => [m, (0.01 + j * 0.007) * (1 + i * 0.08)])
        ),
      })),
      most_inclusive_method:  'plurality',
      least_inclusive_method: 'schulze',
      pedagogical_note:       'Test note.',
    },
  };
}

function renderPanel() {
  return render(
    <MemoryRouter>
      <ElectionProvider>
        <BallotComplexityPanel />
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

describe('BallotComplexityPanel', () => {
  it('shows simulate button', () => {
    renderPanel();
    expect(screen.getByRole('button', { name: /simuler|simulate/i })).toBeInTheDocument();
  });

  it('shows education level slider', () => {
    renderPanel();
    expect(screen.getByTestId('education-slider')).toBeInTheDocument();
  });

  it('shows first-time voter slider', () => {
    renderPanel();
    expect(screen.getByTestId('ftv-slider')).toBeInTheDocument();
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
      expect.stringContaining('/api/election/ballot-complexity'),
      expect.any(Object),
    );
    jest.runAllTimers();
  });

  it('renders bar chart after data loads', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('null-rate-bar-chart')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('renders candidate curve chart after data loads', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('candidate-curve-chart')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows most-inclusive and least-inclusive badges', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByTestId('most-inclusive-badge')).toBeInTheDocument();
      expect(screen.getByTestId('least-inclusive-badge')).toBeInTheDocument();
    });
    jest.runAllTimers();
  });

  it('shows winner-changed badge when at least one method changes winner', async () => {
    mockPost.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('winner-changed-badge')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('does NOT show winner-changed badge when no method changes winner', async () => {
    mockPost.mockResolvedValue(makeData(false));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => screen.getByTestId('most-inclusive-badge'));
    expect(screen.queryByTestId('winner-changed-badge')).not.toBeInTheDocument();
    jest.runAllTimers();
  });

  it('renders results table with one row per method', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('results-table')).toBeInTheDocument());
    for (const m of METHODS) {
      expect(screen.getByTestId(`result-row-${m}`)).toBeInTheDocument();
    }
    jest.runAllTimers();
  });

  it('renders ballot design section', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('ballot-design-section')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('auto-recalculates (debounced) on education slider change after first run', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));

    fireEvent.change(screen.getByTestId('education-slider'), { target: { value: '0.3' } });
    act(() => { jest.advanceTimersByTime(450); });
    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(2));
    jest.runAllTimers();
  });

  it('auto-recalculates on ftv slider change', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));

    fireEvent.change(screen.getByTestId('ftv-slider'), { target: { value: '0.4' } });
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
