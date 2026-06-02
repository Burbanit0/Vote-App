import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import ShyVoterPanel from '../ShyVoterPanel';
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
    error: undefined,
  };
}

function renderPanel() {
  return render(
    <MemoryRouter>
      <QueryClientProvider client={makeTestQueryClient()}>
        <ElectionProvider>
          <ShyVoterPanel />
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

  it('calls API on simulate click', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));
    expect(apiClient.POST).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/(v2\/)?election\/shy-voter/),
      expect.any(Object),
    );
    vi.runAllTimers();
  });

  it('shows poll-winner and real-winner badges after data loads', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByTestId('poll-winner-badge')).toBeInTheDocument();
      expect(screen.getByTestId('real-winner-badge')).toBeInTheDocument();
    });
    vi.runAllTimers();
  });

  it('shows shy-candidate badge', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('shy-candidate-badge')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows polls-wrong alert when polls were wrong', async () => {
    apiClient.POST.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('polls-wrong-alert')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('does NOT show polls-wrong alert when polls were correct', async () => {
    apiClient.POST.mockResolvedValue(makeData(false));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => screen.getByTestId('poll-winner-badge'));
    expect(screen.queryByTestId('polls-wrong-alert')).not.toBeInTheDocument();
    vi.runAllTimers();
  });

  it('shows comparison bar chart', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('comparison-bar-chart')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows poll timeline chart', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('poll-timeline-chart')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows error table with candidate rows', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('error-table')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows systematic error badges per candidate', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByTestId('error-badge-Alice')).toBeInTheDocument();
      expect(screen.getByTestId('error-badge-Bob')).toBeInTheDocument();
    });
    vi.runAllTimers();
  });

  it('debounced re-simulation on slider change', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));

    fireEvent.change(screen.getByTestId('sdf-slider'), { target: { value: '0.7' } });
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
