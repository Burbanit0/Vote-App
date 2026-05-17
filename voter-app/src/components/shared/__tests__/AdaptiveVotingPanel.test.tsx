import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import AdaptiveVotingPanel from '../AdaptiveVotingPanel';
import { ElectionProvider } from '../../../context/ElectionContext';

jest.mock('axios', () => ({ post: jest.fn() }));
const { post: mockPost } = jest.requireMock('axios') as { post: jest.Mock };

jest.mock('recharts', () => {
  const React = require('react');
  return {
    LineChart:           ({ children }: any) => <div data-testid="line-chart">{children}</div>,
    Line:                () => null,
    XAxis:               () => null,
    YAxis:               () => null,
    Tooltip:             () => null,
    Legend:              () => null,
    ReferenceLine:       () => null,
    ResponsiveContainer: ({ children }: any) => <div style={{ width: 400, height: 300 }}>{children}</div>,
  };
});

const makeRound = (rnd: number, winner: string, tacticalPct = 0): any => ({
  round:                rnd,
  vote_shares:          { Alice: 0.45, Bob: 0.35, Carol: 0.20 },
  sincere_shares:       { Alice: 0.40, Bob: 0.38, Carol: 0.22 },
  winner,
  sincere_winner:       'Alice',
  strategic_voters_pct: tacticalPct,
  voter_snapshot: [
    { id: 0, x: -0.3, y: 0.1, sincere_vote: 'Carol', effective_vote: 'Alice', tactical: true },
    { id: 1, x:  0.4, y: -0.1, sincere_vote: 'Bob',   effective_vote: 'Bob',   tactical: false },
  ],
});

const makeData = (winnerChanged = false) => ({
  data: {
    rounds: [
      makeRound(0, 'Alice', 0),
      makeRound(1, winnerChanged ? 'Bob' : 'Alice', 0.12),
      makeRound(2, winnerChanged ? 'Bob' : 'Alice', 0.15),
      makeRound(3, winnerChanged ? 'Bob' : 'Alice', 0.14),
    ],
    converged:          true,
    convergence_round:  2,
    final_winner:       winnerChanged ? 'Bob' : 'Alice',
    sincere_winner:     'Alice',
    strategic_drift:    winnerChanged ? 0.22 : 0.0,
    candidates: [
      { name: 'Alice', x: -0.5 },
      { name: 'Bob',   x:  0.5 },
      { name: 'Carol', x:  0.0 },
    ],
  },
});

function renderPanel() {
  return render(
    <MemoryRouter>
      <ElectionProvider>
        <AdaptiveVotingPanel />
      </ElectionProvider>
    </MemoryRouter>
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
  jest.useFakeTimers();
});

afterEach(() => {
  jest.useRealTimers();
});

describe('AdaptiveVotingPanel', () => {
  it('shows simulate button', () => {
    renderPanel();
    expect(screen.getByRole('button', { name: /simuler|simulate/i })).toBeInTheDocument();
  });

  it('shows prompt before running', () => {
    renderPanel();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('calls axios.post on button click', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));
    expect(mockPost).toHaveBeenCalledWith(
      expect.stringContaining('/api/election/adaptive'),
      expect.any(Object)
    );
  });

  it('renders LineChart after data loads', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByTestId('race-chart')).toBeInTheDocument();
    });
    jest.runAllTimers();
  });

  it('shows convergence badge', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByTestId('convergence-badge')).toBeInTheDocument();
    });
    jest.runAllTimers();
  });

  it('shows final winner badge', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByTestId('final-winner-badge')).toBeInTheDocument();
    });
    jest.runAllTimers();
  });

  it('shows sincere winner badge', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByTestId('sincere-winner-badge')).toBeInTheDocument();
    });
    jest.runAllTimers();
  });

  it('shows drift badge when winner changed and drift > 0.15', async () => {
    mockPost.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByTestId('drift-badge')).toBeInTheDocument();
    });
    jest.runAllTimers();
  });

  it('renders ideology overlay SVG', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByTestId('ideology-overlay')).toBeInTheDocument();
    });
    jest.runAllTimers();
  });

  it('shows warning alert when tacticals changed the winner', async () => {
    mockPost.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      const warnings = document.querySelectorAll('.alert-warning');
      expect(warnings.length).toBeGreaterThan(0);
    });
    jest.runAllTimers();
  });

  it('shows replay button after data loads', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /replay|rejouer/i })).toBeInTheDocument();
    });
    jest.runAllTimers();
  });

  it('shows error on API failure', async () => {
    mockPost.mockRejectedValue(new Error('Network'));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument();
    });
  });
});
