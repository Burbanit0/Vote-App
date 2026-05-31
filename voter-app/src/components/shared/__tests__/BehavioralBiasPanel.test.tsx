import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import BehavioralBiasPanel from '../BehavioralBiasPanel';
import { ElectionProvider } from '../../../stores/useElectionStore';
import { makeTestQueryClient } from '../../../test/queryWrapper';

jest.mock('../../../api/client', () => ({
  apiClient: { GET: jest.fn(), POST: jest.fn(), PUT: jest.fn(), DELETE: jest.fn(), PATCH: jest.fn() },
  getAccessToken: jest.fn(() => null),
}));
const { apiClient } = jest.requireMock('../../../api/client') as { apiClient: { POST: jest.Mock } };

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
    error: undefined,
  };
}

function renderPanel() {
  return render(
    <MemoryRouter>
      <QueryClientProvider client={makeTestQueryClient()}>
        <ElectionProvider>
          <BehavioralBiasPanel />
        </ElectionProvider>
      </QueryClientProvider>
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

  it('calls API on simulate click', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));
    expect(apiClient.POST).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/(v2\/)?election\/behavioral-biases/),
      expect.any(Object),
    );
    jest.runAllTimers();
  });

  it('shows sincere and biased winner badges after load', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      expect(screen.getByTestId('sincere-winner-badge')).toBeInTheDocument();
      expect(screen.getByTestId('biased-winner-badge')).toBeInTheDocument();
    });
    jest.runAllTimers();
  });

  it('shows winner-changed alert when winner changed', async () => {
    apiClient.POST.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('winner-changed-alert')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('does not show winner-changed alert when winner stable', async () => {
    apiClient.POST.mockResolvedValue(makeData(false));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('comparison-banner')).toBeInTheDocument());
    expect(screen.queryByTestId('winner-changed-alert')).not.toBeInTheDocument();
    jest.runAllTimers();
  });

  it('shows method sensitivity table after load', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('sensitivity-table')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows expressive breakdown badge when data includes expressive voters', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('expressive-breakdown-badge')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows bullet breakdown badge', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('bullet-breakdown-badge')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows primacy breakdown badge', async () => {
    apiClient.POST.mockResolvedValue(makeData());
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
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    // Toggle is OFF by default
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));
    const body = (apiClient.POST.mock.calls[0][1] as { body: Record<string, unknown> }).body;
    expect(body.expressive_pct).toBe(0);
    jest.runAllTimers();
  });

  it('sends bullet_voting_pct=0 when toggle is off', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));
    const body = (apiClient.POST.mock.calls[0][1] as { body: Record<string, unknown> }).body;
    expect(body.bullet_voting_pct).toBe(0);
    jest.runAllTimers();
  });

  it('sends primacy_bonus=0 when toggle is off', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));
    const body = (apiClient.POST.mock.calls[0][1] as { body: Record<string, unknown> }).body;
    expect(body.primacy_bonus).toBe(0);
    jest.runAllTimers();
  });

  it('auto-recalculates (debounced) when bias toggle changes after first run', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));

    // Toggle expressive ON → triggers debounced re-run
    fireEvent.click(screen.getByTestId('expressive-switch'));
    act(() => { jest.advanceTimersByTime(450); });
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(2));
    jest.runAllTimers();
  });

  it('shows error on API failure', async () => {
    apiClient.POST.mockRejectedValue(new Error('Network error'));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument());
  });
});
