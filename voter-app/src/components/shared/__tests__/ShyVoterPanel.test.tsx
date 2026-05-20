import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import ShyVoterPanel from '../ShyVoterPanel';
import { ElectionProvider } from '../../../context/ElectionContext';

jest.mock('axios', () => ({ post: jest.fn() }));
const { post: mockPost } = jest.requireMock('axios') as { post: jest.Mock };

jest.mock('recharts', () => {
  const React = require('react');
  return {
    BarChart:            ({ children }: any) => <div>{children}</div>,
    Bar:                 () => null,
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

function makeData(pollsWrong = false) {
  const candidates = ['Alice', 'Bob', 'Carol'];
  return {
    data: {
      real_winner:   pollsWrong ? 'Alice' : 'Bob',
      poll_winner:   'Bob',
      polls_wrong:   pollsWrong,
      shy_candidate: 'Alice',
      poll_results:  Array.from({ length: 10 }, (_, i) => ({
        poll_n: i + 1,
        predicted: { Alice: 0.22, Bob: 0.45, Carol: 0.33 },
        real:      { Alice: 0.35, Bob: 0.40, Carol: 0.25 },
      })),
      systematic_error:  { Alice: -0.13, Bob: 0.05, Carol: 0.08 },
      real_results:      { Alice: 0.35, Bob: 0.40, Carol: 0.25 },
      avg_poll_results:  { Alice: 0.22, Bob: 0.45, Carol: 0.33 },
      social_desirability_curve: Array.from({ length: 11 }, (_, i) => ({
        factor:          i / 10,
        poll_error:      i * 0.035,
        winner_wrong_pct: i >= 7 ? 1.0 : 0.0,
      })),
      pedagogical_note: 'Test note.',
    },
  };
}

function renderPanel() {
  return render(
    <MemoryRouter>
      <ElectionProvider>
        <ShyVoterPanel />
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

describe('ShyVoterPanel', () => {
  it('shows simulate button', () => {
    renderPanel();
    expect(screen.getByRole('button', { name: /simuler|simulate/i })).toBeInTheDocument();
  });

  it('shows social desirability factor slider', () => {
    renderPanel();
    expect(screen.getByTestId('sdf-slider')).toBeInTheDocument();
  });

  it('shows shy candidate selector', () => {
    renderPanel();
    expect(screen.getByTestId('shy-candidate-select')).toBeInTheDocument();
  });

  it('shows prompt before first run', () => {
    renderPanel();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('always shows historical examples section', () => {
    renderPanel();
    expect(screen.getByTestId('historical-section')).toBeInTheDocument();
  });

  it('calls axios.post on simulate click', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));
    expect(mockPost).toHaveBeenCalledWith(
      expect.stringContaining('/api/election/shy-voter'),
      expect.any(Object),
    );
    jest.runAllTimers();
  });

  it('shows poll-winner and real-winner badges after data loads', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByTestId('poll-winner-badge')).toBeInTheDocument();
      expect(screen.getByTestId('real-winner-badge')).toBeInTheDocument();
    });
    jest.runAllTimers();
  });

  it('shows shy-candidate badge', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('shy-candidate-badge')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows polls-wrong alert when polls were wrong', async () => {
    mockPost.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('polls-wrong-alert')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('does NOT show polls-wrong alert when polls were correct', async () => {
    mockPost.mockResolvedValue(makeData(false));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => screen.getByTestId('poll-winner-badge'));
    expect(screen.queryByTestId('polls-wrong-alert')).not.toBeInTheDocument();
    jest.runAllTimers();
  });

  it('shows comparison bar chart', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('comparison-bar-chart')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows poll timeline chart', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('poll-timeline-chart')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows error table with candidate rows', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('error-table')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows systematic error badges per candidate', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByTestId('error-badge-Alice')).toBeInTheDocument();
      expect(screen.getByTestId('error-badge-Bob')).toBeInTheDocument();
    });
    jest.runAllTimers();
  });

  it('debounced re-simulation on slider change', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));

    fireEvent.change(screen.getByTestId('sdf-slider'), { target: { value: '0.7' } });
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
