import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import CompulsoryVotingPanel from '../CompulsoryVotingPanel';
import { ElectionProvider } from '../../../context/ElectionContext';

jest.mock('axios', () => ({ post: jest.fn() }));
const { post: mockPost } = jest.requireMock('axios') as { post: jest.Mock };

jest.mock('recharts', () => {
  const React = require('react');
  return {
    BarChart:            ({ children }: any) => <div>{children}</div>,
    Bar:                 () => null,
    Cell:                () => null,
    XAxis:               () => null,
    YAxis:               () => null,
    CartesianGrid:       () => null,
    Tooltip:             () => null,
    Legend:              () => null,
    ResponsiveContainer: ({ children }: any) => <div style={{ width: 400, height: 100 }}>{children}</div>,
  };
});

// ── Fixture ───────────────────────────────────────────────────────────────────

function makeData(winnerChanged = false) {
  return {
    data: {
      voluntary: {
        turnout:     0.65,
        winner:      'Alice',
        vote_shares: { Alice: 0.44, Bob: 0.33, Carol: 0.23 },
        null_rate:   0.0,
        voter_profile: { mean_ideology_x: 0.08, partisan_pct: 0.45 },
      },
      compulsory: {
        turnout:          0.92,
        winner:           winnerChanged ? 'Bob' : 'Alice',
        vote_shares:      { Alice: winnerChanged ? 0.35 : 0.42, Bob: winnerChanged ? 0.43 : 0.35, Carol: 0.23 },
        null_rate:        0.035,
        reluctant_count:  81,
        noise_effect:     0.04,
      },
      winner_changed:             winnerChanged,
      representation_improvement: 0.06,
      quality_degradation:        0.04,
      pedagogical_note:           'Test note.',
    },
  };
}

function renderPanel() {
  return render(
    <MemoryRouter>
      <ElectionProvider>
        <CompulsoryVotingPanel />
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

  it('calls axios.post on simulate click', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));
    expect(mockPost).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/(v2\/)?election\/compulsory-voting/),
      expect.any(Object),
    );
    jest.runAllTimers();
  });

  it('shows voluntary and compulsory result cards', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByTestId('voluntary-card')).toBeInTheDocument();
      expect(screen.getByTestId('compulsory-card')).toBeInTheDocument();
    });
    jest.runAllTimers();
  });

  it('shows metrics row with representation and quality badges', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByTestId('metrics-row')).toBeInTheDocument();
      expect(screen.getByTestId('representation-badge')).toBeInTheDocument();
      expect(screen.getByTestId('quality-badge')).toBeInTheDocument();
    });
    jest.runAllTimers();
  });

  it('shows reluctant badge', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('reluctant-badge')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows winner-changed alert when winner changed', async () => {
    mockPost.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('winner-changed-alert')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('does NOT show winner-changed alert when winner stable', async () => {
    mockPost.mockResolvedValue(makeData(false));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => screen.getByTestId('voluntary-card'));
    expect(screen.queryByTestId('winner-changed-alert')).not.toBeInTheDocument();
    jest.runAllTimers();
  });

  it('debounced re-simulation on vol-turnout slider change', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));

    fireEvent.change(screen.getByTestId('vol-turnout-slider'), { target: { value: '0.55' } });
    act(() => { jest.advanceTimersByTime(450); });
    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(2));
    jest.runAllTimers();
  });

  it('debounced re-simulation on random-pct slider', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));

    fireEvent.change(screen.getByTestId('random-pct-slider'), { target: { value: '0.25' } });
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
