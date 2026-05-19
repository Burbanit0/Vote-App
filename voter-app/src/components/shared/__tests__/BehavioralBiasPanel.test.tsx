import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import BehavioralBiasPanel from '../BehavioralBiasPanel';
import { ElectionProvider } from '../../../context/ElectionContext';

jest.mock('axios', () => ({ post: jest.fn() }));
const { post: mockPost } = jest.requireMock('axios') as { post: jest.Mock };

// ── Fixture ───────────────────────────────────────────────────────────────────

function makeData(winnerChanged = false) {
  return {
    data: {
      sincere_winner: 'Alice',
      biased_winner:  winnerChanged ? 'Bob' : 'Alice',
      winner_changed: winnerChanged,
      vote_breakdown: {
        expressive_voters: 20,
        bullet_voters:     20,
        primacy_affected:  2,
        first_listed:      'Carol',
        candidate_order:   ['Carol', 'Alice', 'Bob'],
      },
      method_sensitivity: {
        plurality: { sincere: 'Alice', biased: winnerChanged ? 'Bob' : 'Alice' },
        approval:  { sincere: 'Alice', biased: winnerChanged ? 'Bob' : 'Alice' },
        borda:     { sincere: 'Alice', biased: 'Alice' },
        irv:       { sincere: 'Alice', biased: 'Alice' },
        schulze:   { sincere: 'Alice', biased: 'Alice' },
        majority_judgment: { sincere: 'Alice', biased: 'Alice' },
      },
      bullet_immune_methods: ['majority_judgment', 'borda', 'irv', 'schulze', 'star_voting'],
      pedagogical_note: 'Test note.',
    },
  };
}

function renderPanel() {
  return render(
    <MemoryRouter>
      <ElectionProvider>
        <BehavioralBiasPanel />
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

describe('BehavioralBiasPanel', () => {
  it('shows simulate button', () => {
    renderPanel();
    expect(screen.getByRole('button', { name: /simuler|simulate/i })).toBeInTheDocument();
  });

  it('shows three bias toggle switches', () => {
    renderPanel();
    expect(screen.getByTestId('expressive-switch')).toBeInTheDocument();
    expect(screen.getByTestId('bullet-switch')).toBeInTheDocument();
    expect(screen.getByTestId('primacy-switch')).toBeInTheDocument();
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
      expect.stringContaining('/api/election/behavioral-biases'),
      expect.any(Object),
    );
    jest.runAllTimers();
  });

  it('shows sincere and biased winner badges after load', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByTestId('sincere-winner-badge')).toBeInTheDocument();
      expect(screen.getByTestId('biased-winner-badge')).toBeInTheDocument();
    });
    jest.runAllTimers();
  });

  it('shows winner-changed alert when winner changed', async () => {
    mockPost.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('winner-changed-alert')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('does not show winner-changed alert when winner stable', async () => {
    mockPost.mockResolvedValue(makeData(false));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('comparison-banner')).toBeInTheDocument());
    expect(screen.queryByTestId('winner-changed-alert')).not.toBeInTheDocument();
    jest.runAllTimers();
  });

  it('shows method sensitivity table after load', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('sensitivity-table')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows expressive breakdown badge when data includes expressive voters', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('expressive-breakdown-badge')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows bullet breakdown badge', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('bullet-breakdown-badge')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows primacy breakdown badge', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('primacy-breakdown-badge')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('expressive toggle shows slider when enabled', () => {
    renderPanel();
    const sw = screen.getByTestId('expressive-switch');
    fireEvent.click(sw);
    expect(screen.getByTestId('expressive-slider')).toBeInTheDocument();
  });

  it('bullet toggle shows slider when enabled', () => {
    renderPanel();
    fireEvent.click(screen.getByTestId('bullet-switch'));
    expect(screen.getByTestId('bullet-slider')).toBeInTheDocument();
  });

  it('primacy toggle shows ballot and slider when enabled', () => {
    renderPanel();
    fireEvent.click(screen.getByTestId('primacy-switch'));
    expect(screen.getByTestId('primacy-slider')).toBeInTheDocument();
    expect(screen.getByTestId('draggable-ballot')).toBeInTheDocument();
  });

  it('sends expressive_pct=0 when toggle is off', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    // Toggle is OFF by default
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));
    const body = mockPost.mock.calls[0][1];
    expect(body.expressive_pct).toBe(0);
    jest.runAllTimers();
  });

  it('sends bullet_voting_pct=0 when toggle is off', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));
    const body = mockPost.mock.calls[0][1];
    expect(body.bullet_voting_pct).toBe(0);
    jest.runAllTimers();
  });

  it('sends primacy_bonus=0 when toggle is off', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));
    const body = mockPost.mock.calls[0][1];
    expect(body.primacy_bonus).toBe(0);
    jest.runAllTimers();
  });

  it('auto-recalculates (debounced) when bias toggle changes after first run', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));

    // Toggle expressive ON → triggers debounced re-run
    fireEvent.click(screen.getByTestId('expressive-switch'));
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
