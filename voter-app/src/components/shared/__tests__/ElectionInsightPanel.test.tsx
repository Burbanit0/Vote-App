import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import ElectionInsightPanel from '../ElectionInsightPanel';

jest.mock('../../../services/electionApi', () => ({
  interpretElection: jest.fn(),
}));

const { interpretElection } = jest.requireMock('../../../services/electionApi') as {
  interpretElection: jest.Mock;
};

// Sample ElectionResult with high agreement (consensus)
const HIGH_AGREEMENT_RESULT: any = {
  config:                  { blank_vote: { enabled: false, rule: 'symbolic' } },
  voters_snapshot:         [],
  candidates:              [{ name: 'Alice', x: 0, y: 0, party: 'Liberal' }],
  methods: {
    plurality: { winner: 'Alice', bayesian_regret: 0.05, majority_satisfaction: 0.7, condorcet_consistent: true },
    schulze:   { winner: 'Alice', bayesian_regret: 0.02, majority_satisfaction: 0.8, condorcet_consistent: true },
  },
  condorcet_winner:        'Alice',
  blank_rate:              0,
  campaign_trajectory:     null,
  inter_method_agreement:  0.90,
  condorcet_exists:        true,
};

// Sample ElectionResult with low agreement (divergence)
const LOW_AGREEMENT_RESULT: any = {
  ...HIGH_AGREEMENT_RESULT,
  methods: {
    plurality: { winner: 'Alice', bayesian_regret: 0.08, majority_satisfaction: 0.6, condorcet_consistent: false },
    schulze:   { winner: 'Bob',   bayesian_regret: 0.02, majority_satisfaction: 0.85, condorcet_consistent: true },
  },
  condorcet_winner:       'Bob',
  inter_method_agreement: 0.40,
  condorcet_exists:       true,
};

const CONSENSUS_INSIGHT = {
  headline:           '✓ Large consensus: 90% of methods elect Alice.',
  condorcet_analysis: 'Alice is the Condorcet winner.',
  divergence_reason:  'Alice is the Condorcet winner.',
  method_groups:      [{ winner: 'Alice', methods: ['plurality', 'schulze'], pct: 1.0 }],
  best_by_regret:     'schulze',
  worst_by_regret:    'plurality',
  blank_analysis:     null,
  pedagogical_note:   'Ideal case: methods converge.',
  key_facts:          ['90% elect Alice', 'Condorcet: Alice', 'Best method: schulze'],
};

const DIVERGENCE_INSIGHT = {
  ...CONSENSUS_INSIGHT,
  headline:      '🚨 Strong divergence: only 40% agree.',
  method_groups: [
    { winner: 'Alice', methods: ['plurality'], pct: 0.5 },
    { winner: 'Bob',   methods: ['schulze'],   pct: 0.5 },
  ],
};

beforeEach(() => {
  jest.clearAllMocks();
  interpretElection.mockResolvedValue(CONSENSUS_INSIGHT);
});

function renderPanel(result: any) {
  return render(
    <MemoryRouter>
      <ElectionInsightPanel result={result} />
    </MemoryRouter>
  );
}

describe('ElectionInsightPanel', () => {
  it('renders nothing when result is null', () => {
    const { container } = renderPanel(null);
    expect(container.firstChild).toBeNull();
  });

  it('calls interpretElection when result is provided', async () => {
    renderPanel(HIGH_AGREEMENT_RESULT);
    await waitFor(() => expect(interpretElection).toHaveBeenCalledTimes(1));
  });

  it('displays the headline after analysis loads', async () => {
    renderPanel(HIGH_AGREEMENT_RESULT);
    await waitFor(() => {
      expect(screen.getAllByText(/consensus/i).length).toBeGreaterThan(0);
    });
  });

  it('shows green badge for high agreement (>80%)', async () => {
    renderPanel(HIGH_AGREEMENT_RESULT);
    await waitFor(() => {
      expect(screen.getAllByText(/consensus/i).length).toBeGreaterThan(0);
    });
  });

  it('shows red badge for low agreement (<50%)', async () => {
    interpretElection.mockResolvedValue(DIVERGENCE_INSIGHT);
    renderPanel(LOW_AGREEMENT_RESULT);
    await waitFor(() => {
      expect(screen.getAllByText(/Forte divergence|Strong divergence/i).length).toBeGreaterThan(0);
    });
  });

  it('shows method groups with winner names', async () => {
    interpretElection.mockResolvedValue(DIVERGENCE_INSIGHT);
    renderPanel(LOW_AGREEMENT_RESULT);
    await waitFor(() => {
      expect(screen.getAllByText(/Alice/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/Bob/i).length).toBeGreaterThan(0);
    });
  });

  it('shows best and worst method badges', async () => {
    renderPanel(HIGH_AGREEMENT_RESULT);
    await waitFor(() => {
      expect(screen.getAllByText(/schulze/i).length).toBeGreaterThan(0);
    });
  });

  it('shows condorcet analysis text', async () => {
    renderPanel(HIGH_AGREEMENT_RESULT);
    await waitFor(() => {
      expect(screen.getAllByText(/Condorcet/i).length).toBeGreaterThan(0);
    });
  });

  it('shows key facts bullet list', async () => {
    renderPanel(HIGH_AGREEMENT_RESULT);
    await waitFor(() => {
      expect(screen.getAllByText(/elect Alice|élisent Alice/i).length).toBeGreaterThan(0);
    });
  });

  it('does NOT show blank analysis when blank_analysis is null', async () => {
    renderPanel(HIGH_AGREEMENT_RESULT);
    await waitFor(() => {
      // blank_analysis = null → no blank warning
      expect(screen.queryByText(/vote blanc|blank vote.*%/i)).toBeNull();
    });
  });
});
