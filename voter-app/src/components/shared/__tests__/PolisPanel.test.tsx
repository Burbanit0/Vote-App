import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import PolisPanel from '../PolisPanel';
import { ElectionProvider } from '../../../context/ElectionContext';
import { makeTestQueryClient } from '../../../test/queryWrapper';

jest.mock('../../../api/client', () => ({
  apiClient: { GET: jest.fn(), POST: jest.fn(), PUT: jest.fn(), DELETE: jest.fn(), PATCH: jest.fn() },
  getAccessToken: jest.fn(() => null),
}));
const { apiClient } = jest.requireMock('../../../api/client') as { apiClient: { POST: jest.Mock } };

// ── Fixture ───────────────────────────────────────────────────────────────────

function makeData(winnersAgree = true) {
  const STMTS = [
    { text: 'Proposition A', global_approval: 0.88, is_consensus: true,  is_polarizing: false, cluster_approvals: [0.90, 0.85, 0.88] },
    { text: 'Proposition B', global_approval: 0.35, is_consensus: false, is_polarizing: true,  cluster_approvals: [0.70, 0.15, 0.40] },
    { text: 'Proposition C', global_approval: 0.55, is_consensus: false, is_polarizing: false, cluster_approvals: [0.55, 0.55, 0.55] },
  ];
  return {
    data: {
      clusters: [
        { id: 0, size: 35, label: 'progressistes', center: { x: -0.6, y: 0.1 }, votes: { 0: 0.90, 1: 0.70, 2: 0.55 } },
        { id: 1, size: 35, label: 'conservateurs', center: { x:  0.6, y: 0.1 }, votes: { 0: 0.85, 1: 0.15, 2: 0.55 } },
        { id: 2, size: 30, label: 'groupe 3',      center: { x:  0.0, y: 0.5 }, votes: { 0: 0.88, 1: 0.40, 2: 0.55 } },
      ],
      statements: STMTS,
      participant_positions: Array.from({ length: 20 }, (_, i) => ({
        id: i, x_pca: (i - 10) * 0.1, y_pca: (i - 10) * 0.05,
        cluster_id: i % 3,
      })),
      polis_winner:    'Carol',
      election_winner: winnersAgree ? 'Carol' : 'Alice',
      winners_agree:   winnersAgree,
      consensus_count:       1,
      polarizing_count:      1,
      silent_majority_count: 0,
      candidate_scores: { Alice: 0.72, Bob: 0.68, Carol: 0.88 },
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
          <PolisPanel />
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

describe('PolisPanel', () => {
  it('shows simulate button', () => {
    renderPanel();
    expect(screen.getByTestId('simulate-btn')).toBeInTheDocument();
  });

  it('shows ideology selector', () => {
    renderPanel();
    expect(screen.getByTestId('ideology-select')).toBeInTheDocument();
  });

  it('shows clusters input', () => {
    renderPanel();
    expect(screen.getByTestId('clusters-input')).toBeInTheDocument();
  });

  it('shows threshold slider', () => {
    renderPanel();
    expect(screen.getByTestId('threshold-slider')).toBeInTheDocument();
  });

  it('shows prompt before first run', () => {
    renderPanel();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('calls API on simulate click', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));
    expect(apiClient.POST).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/(v2\/)?tech\/polis/),
      expect.any(Object),
    );
    jest.runAllTimers();
  });

  it('shows scatter plot SVG after data loads', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('polis-scatter-svg')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows winner comparison section', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => {
      expect(screen.getByTestId('winner-comparison')).toBeInTheDocument();
      expect(screen.getByTestId('polis-winner-badge')).toBeInTheDocument();
      expect(screen.getByTestId('election-winner-badge')).toBeInTheDocument();
    });
    jest.runAllTimers();
  });

  it('shows divergence alert when winners disagree', async () => {
    apiClient.POST.mockResolvedValue(makeData(false));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('winners-diverge-alert')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('does NOT show divergence alert when winners agree', async () => {
    apiClient.POST.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => screen.getByTestId('winner-comparison'));
    expect(screen.queryByTestId('winners-diverge-alert')).not.toBeInTheDocument();
    jest.runAllTimers();
  });

  it('shows count badges', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => {
      expect(screen.getByTestId('consensus-count-badge')).toBeInTheDocument();
      expect(screen.getByTestId('polarizing-count-badge')).toBeInTheDocument();
      expect(screen.getByTestId('silent-majority-badge')).toBeInTheDocument();
    });
    jest.runAllTimers();
  });

  it('renders statement table', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('statement-table')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('filters to consensus only when filter clicked', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => screen.getByTestId('filter-consensus'));
    fireEvent.click(screen.getByTestId('filter-consensus'));
    // Only consensus rows should be visible
    const table = screen.getByTestId('statement-table');
    const rows = table.querySelectorAll('tbody tr');
    expect(rows.length).toBe(1); // only 1 consensus statement in fixture
    jest.runAllTimers();
  });

  it('shows Taiwan examples sidebar', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('taiwan-examples')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows error on API failure', async () => {
    apiClient.POST.mockRejectedValue(new Error('Network error'));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument());
  });
});
