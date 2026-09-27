import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import ElectionInsightPanel from '../ElectionInsightPanel';

vi.mock('../../../../services/electionApi', () => ({
  interpretElection: vi.fn(),
}));

const { interpretElection } = (await import('../../../../services/electionApi')) as unknown as {
  interpretElection: jest.Mock;
};

// Sample ElectionResult with high agreement (consensus)
const HIGH_AGREEMENT_RESULT: any = {
  config: { blank_vote: { enabled: false, rule: 'symbolic' } },
  voters_snapshot: [],
  candidates: [{ name: 'Alice', x: 0, y: 0, party: 'Liberal' }],
  methods: {
    plurality: {
      winner: 'Alice',
      bayesian_regret: 0.05,
      majority_satisfaction: 0.7,
      condorcet_consistent: true,
    },
    schulze: {
      winner: 'Alice',
      bayesian_regret: 0.02,
      majority_satisfaction: 0.8,
      condorcet_consistent: true,
    },
  },
  condorcet_winner: 'Alice',
  blank_rate: 0,
  campaign_trajectory: null,
  inter_method_agreement: 0.9,
  condorcet_exists: true,
};

// Sample ElectionResult with low agreement (divergence)
const LOW_AGREEMENT_RESULT: any = {
  ...HIGH_AGREEMENT_RESULT,
  methods: {
    plurality: {
      winner: 'Alice',
      bayesian_regret: 0.08,
      majority_satisfaction: 0.6,
      condorcet_consistent: false,
    },
    schulze: {
      winner: 'Bob',
      bayesian_regret: 0.02,
      majority_satisfaction: 0.85,
      condorcet_consistent: true,
    },
  },
  condorcet_winner: 'Bob',
  inter_method_agreement: 0.4,
  condorcet_exists: true,
};

const CONSENSUS_INSIGHT = {
  headline: '✓ Large consensus: 90% of methods elect Alice.',
  condorcet_analysis: 'Alice is the Condorcet winner.',
  divergence_reason: 'Alice is the Condorcet winner.',
  method_groups: [{ winner: 'Alice', methods: ['plurality', 'schulze'], pct: 1.0 }],
  // Both methods elect Alice, so they score the same regret: no best or worst.
  best_by_regret: [],
  worst_by_regret: [],
  blank_analysis: null,
  pedagogical_note: 'Ideal case: methods converge.',
  key_facts: ['90% elect Alice', 'Condorcet: Alice'],
};

const DIVERGENCE_INSIGHT = {
  ...CONSENSUS_INSIGHT,
  headline: '🚨 Strong divergence: only 40% agree.',
  method_groups: [
    { winner: 'Alice', methods: ['plurality'], pct: 0.5 },
    { winner: 'Bob', methods: ['schulze'], pct: 0.5 },
  ],
  best_by_regret: ['schulze'],
  worst_by_regret: ['plurality'],
};

beforeEach(() => {
  vi.clearAllMocks();
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

  it('names the outcome, not one method, when a whole group ties', async () => {
    // Regret is a property of the winner: plurality, borda and irv all elect
    // Alice, so all three share the lowest regret. The badge used to print
    // whichever the backend listed first as "the most fair method".
    const methods = {
      plurality: { winner: 'Alice', bayesian_regret: 0.02 },
      borda: { winner: 'Alice', bayesian_regret: 0.02 },
      irv: { winner: 'Alice', bayesian_regret: 0.02 },
      approval: { winner: 'Bob', bayesian_regret: 0.09 },
      star: { winner: 'Bob', bayesian_regret: 0.09 },
      schulze: { winner: 'Alice', bayesian_regret: 0.02 },
      coombs: { winner: 'Bob', bayesian_regret: 0.09 },
      minimax: { winner: 'Bob', bayesian_regret: 0.09 },
    };
    interpretElection.mockResolvedValue({
      ...DIVERGENCE_INSIGHT,
      best_by_regret: ['plurality', 'borda', 'irv', 'schulze'],
      worst_by_regret: ['approval', 'star', 'coombs', 'minimax'],
    });
    renderPanel({ ...LOW_AGREEMENT_RESULT, methods });
    await waitFor(() => {
      expect(screen.getByText(/Lowest regret: Alice \(\s*4\/8 methods\s*\)/)).toBeInTheDocument();
    });
    expect(
      screen.getByText(/Highest regret: approval, star, coombs \+1 →\s*Bob/)
    ).toBeInTheDocument();
  });

  it('shows no regret badges when every method ties', async () => {
    renderPanel(HIGH_AGREEMENT_RESULT);
    await waitFor(() => {
      expect(screen.getByText(CONSENSUS_INSIGHT.headline)).toBeInTheDocument();
    });
    expect(screen.queryByText(/regret/i)).not.toBeInTheDocument();
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
