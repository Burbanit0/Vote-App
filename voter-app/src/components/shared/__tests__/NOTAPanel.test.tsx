import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import NOTAPanel from '../NOTAPanel';
import { ElectionProvider } from '../../../context/ElectionContext';

jest.mock('axios', () => ({ post: jest.fn() }));
const { post: mockPost } = jest.requireMock('axios') as { post: jest.Mock };

jest.mock('recharts', () => {
  const React = require('react');
  return {
    LineChart:           ({ children }: any) => <div data-testid="nota-line-chart">{children}</div>,
    Line:                ({ name }: any) => <div data-testid={`line-${name ?? 'unknown'}`} />,
    XAxis:               () => null,
    YAxis:               () => null,
    CartesianGrid:       () => null,
    Tooltip:             () => null,
    Legend:              () => null,
    ReferenceLine:       () => null,
    ResponsiveContainer: ({ children }: any) => <div style={{ width: 400, height: 200 }}>{children}</div>,
  };
});

// ── Fixtures ──────────────────────────────────────────────────────────────────

function makeData(valid = true, notaPct = 0.15, winner: string | null = 'Alice') {
  return {
    data: {
      nota_pct:       notaPct,
      election_valid: valid,
      winner,
      nota_curve: Array.from({ length: 20 }, (_, i) => ({
        threshold: i * 0.05,
        nota_pct:  Math.min(1, i * 0.05),
        nota_wins: i * 0.05 >= 0.5,
        winner:    i * 0.05 >= 0.5 ? null : 'Alice',
      })),
      method_comparison: {
        plurality:         { winner: 'Alice', nota_pct: notaPct,        election_valid: valid },
        approval:          { winner: 'Alice', nota_pct: notaPct * 0.5,  election_valid: true  },
        borda:             { winner: 'Alice', nota_pct: notaPct * 0.95, election_valid: valid },
        irv:               { winner: 'Alice', nota_pct: notaPct * 0.95, election_valid: valid },
        schulze:           { winner: 'Alice', nota_pct: notaPct * 0.9,  election_valid: valid },
        majority_judgment: { winner: 'Alice', nota_pct: notaPct * 0.7,  election_valid: valid },
      },
      pedagogical_note:  'Test note.',
      nota_rule:         'invalidate',
      nota_threshold:    0.3,
    },
  };
}

function renderPanel() {
  return render(
    <MemoryRouter>
      <ElectionProvider>
        <NOTAPanel />
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

describe('NOTAPanel', () => {
  it('shows simulate button', () => {
    renderPanel();
    expect(screen.getByRole('button', { name: /simuler|simulate/i })).toBeInTheDocument();
  });

  it('shows threshold slider', () => {
    renderPanel();
    expect(screen.getByTestId('nota-threshold-slider')).toBeInTheDocument();
  });

  it('shows rule selector', () => {
    renderPanel();
    expect(screen.getByTestId('nota-rule-select')).toBeInTheDocument();
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
      expect.stringMatching(/\/api\/(v2\/)?election\/nota/),
      expect.any(Object),
    );
    jest.runAllTimers();
  });

  it('shows NOTA percentage badge after load', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('nota-pct-badge')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows election-valid badge when election valid', async () => {
    mockPost.mockResolvedValue(makeData(true, 0.1, 'Alice'));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('election-valid-badge')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows election-invalid alert when election invalid', async () => {
    mockPost.mockResolvedValue(makeData(false, 0.6, null));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('election-invalid-alert')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('does NOT show invalid alert when threshold is low (election valid)', async () => {
    // Slider at 0 / low nota_pct → no invalid badge
    mockPost.mockResolvedValue(makeData(true, 0.0, 'Alice'));
    renderPanel();
    // Set slider to 0
    fireEvent.change(screen.getByTestId('nota-threshold-slider'), { target: { value: '0' } });
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('election-valid-badge')).toBeInTheDocument());
    expect(screen.queryByTestId('election-invalid-alert')).not.toBeInTheDocument();
    jest.runAllTimers();
  });

  it('shows tipping point badge when nota exceeds 50%', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('tipping-point-badge')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('renders nota curve chart', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('nota-curve-chart')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('renders method comparison table', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('method-comparison-table')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('has a row for each tracked method', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      for (const meth of ['plurality', 'approval', 'borda', 'irv', 'schulze', 'majority_judgment']) {
        expect(screen.getByTestId(`method-row-${meth}`)).toBeInTheDocument();
      }
    });
    jest.runAllTimers();
  });

  it('shows nota-elected alert when NOTA wins with winner_take_all rule', async () => {
    mockPost.mockResolvedValue(makeData(true, 0.6, 'NOTA'));
    renderPanel();
    fireEvent.change(screen.getByTestId('nota-rule-select'), { target: { value: 'winner_take_all' } });
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('nota-elected-alert')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('debounced re-simulation on slider change', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));

    fireEvent.change(screen.getByTestId('nota-threshold-slider'), { target: { value: '0.7' } });
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
