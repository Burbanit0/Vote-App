import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import JudgmentAggregationPanel from '../JudgmentAggregationPanel';

jest.mock('axios', () => ({ post: jest.fn() }));
const { post: mockPost } = jest.requireMock('axios') as { post: jest.Mock };

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
  };
}

function renderPanel() {
  return render(
    <MemoryRouter>
      <JudgmentAggregationPanel />
    </MemoryRouter>
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  jest.useFakeTimers();
});

afterEach(() => { jest.useRealTimers(); });

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

  it('calls axios.post on simulate click', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));
    expect(mockPost).toHaveBeenCalledWith(
      expect.stringContaining('/api/theory/judgment-aggregation'),
      expect.any(Object),
    );
    jest.runAllTimers();
  });

  it('shows coherent badge (success) when coherent', async () => {
    mockPost.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => {
      const badge = screen.getByTestId('coherence-badge');
      expect(badge.className).toContain('bg-success');
    });
    jest.runAllTimers();
  });

  it('shows incoherent badge (danger) when incoherent', async () => {
    mockPost.mockResolvedValue(makeData(false));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => {
      const badge = screen.getByTestId('coherence-badge');
      expect(badge.className).toContain('bg-danger');
    });
    jest.runAllTimers();
  });

  it('shows voter coherence badge', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('voter-coherence-badge')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows propositions table', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('propositions-table')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows incoherence alert when incoherent', async () => {
    mockPost.mockResolvedValue(makeData(false));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('incoherence-alert')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('does NOT show incoherence alert when coherent', async () => {
    mockPost.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => screen.getByTestId('coherence-badge'));
    expect(screen.queryByTestId('incoherence-alert')).not.toBeInTheDocument();
    jest.runAllTimers();
  });

  it('renders logic tree SVG', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('logic-tree-svg')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows resolution card when incoherent', async () => {
    mockPost.mockResolvedValue(makeData(false));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('resolution-card')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows severity badge when paradox exists', async () => {
    mockPost.mockResolvedValue(makeData(false));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('severity-badge')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows error on API failure', async () => {
    mockPost.mockRejectedValue(new Error('Network error'));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument());
  });
});
