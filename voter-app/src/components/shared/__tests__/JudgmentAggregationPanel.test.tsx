import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import JudgmentAggregationPanel from '../JudgmentAggregationPanel';
import { makeTestQueryClient } from '../../../test/queryWrapper';

vi.mock('../../../api/client', () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn(), PATCH: vi.fn() },
  getAccessToken: vi.fn(() => null),
}));
const { apiClient } = (await import('../../../api/client')) as unknown as { apiClient: { POST: jest.Mock } };

// ── Fixtures ──────────────────────────────────────────────────────────────────

function makeData(coherent = false) {
  const incoherences = coherent ? [] : [
    { premises: ['P1', 'P2'], conclusion: 'C', problem: 'Prémisses acceptées, conclusion rejetée' },
  ];
  return {
    data: {
      scenario:           'legal',
      scenario_name:      'Responsabilité contractuelle',
      propositions: [
        { text: 'Le contrat existait',                    type: 'premise',    id: 'P1', yes_pct: 0.67, collective_vote: true },
        { text: 'Les obligations non remplies',           type: 'premise',    id: 'P2', yes_pct: 0.67, collective_vote: true },
        { text: 'Responsabilité contractuelle',           type: 'conclusion', id: 'C',  yes_pct: 0.33, collective_vote: !coherent },
      ],
      collective_coherent:  coherent,
      incoherences,
      voter_coherence_rate: 1.0,
      paradox_severity:     coherent ? 0 : 1.0,
      resolution_methods: {
        premise_based:    { C: true },
        conclusion_based: { premise_override: true },
      },
      pedagogical_note: 'Test note.',
    },
    error: undefined,
  };
}

function renderPanel() {
  return render(
    <MemoryRouter>
      <QueryClientProvider client={makeTestQueryClient()}>
        <JudgmentAggregationPanel />
      </QueryClientProvider>
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.useFakeTimers();
});

afterEach(() => { vi.useRealTimers(); });

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('JudgmentAggregationPanel', () => {
  it('shows simulate button', () => {
    renderPanel();
    expect(screen.getByTestId('simulate-btn')).toBeInTheDocument();
  });

  it('shows scenario selector', () => {
    renderPanel();
    expect(screen.getByTestId('scenario-select')).toBeInTheDocument();
  });

  it('shows num-voters and seed inputs', () => {
    renderPanel();
    expect(screen.getByTestId('num-voters-input')).toBeInTheDocument();
    expect(screen.getByTestId('seed-input')).toBeInTheDocument();
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
      expect.stringMatching(/\/api\/(v2\/)?theory\/judgment-aggregation/),
      expect.any(Object),
    );
    vi.runAllTimers();
  });

  it('shows coherent badge (success) when coherent', async () => {
    apiClient.POST.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => {
      const badge = screen.getByTestId('coherence-badge');
      expect(badge.className).toContain('bg-[#198754]');
    });
    vi.runAllTimers();
  });

  it('shows incoherent badge (danger) when incoherent', async () => {
    apiClient.POST.mockResolvedValue(makeData(false));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => {
      const badge = screen.getByTestId('coherence-badge');
      expect(badge.className).toContain('bg-[#dc3545]');
    });
    vi.runAllTimers();
  });

  it('shows voter coherence badge', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('voter-coherence-badge')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows propositions table', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('propositions-table')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows incoherence alert when incoherent', async () => {
    apiClient.POST.mockResolvedValue(makeData(false));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('incoherence-alert')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('does NOT show incoherence alert when coherent', async () => {
    apiClient.POST.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => screen.getByTestId('coherence-badge'));
    expect(screen.queryByTestId('incoherence-alert')).not.toBeInTheDocument();
    vi.runAllTimers();
  });

  it('renders logic tree SVG', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('logic-tree-svg')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows resolution card when incoherent', async () => {
    apiClient.POST.mockResolvedValue(makeData(false));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('resolution-card')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows severity badge when paradox exists', async () => {
    apiClient.POST.mockResolvedValue(makeData(false));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('severity-badge')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows error on API failure', async () => {
    apiClient.POST.mockRejectedValue(new Error('Network error'));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument());
  });
});
