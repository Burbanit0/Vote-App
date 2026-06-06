import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import HistoricalReferencePanel from '../HistoricalReferencePanel';

// Mock the ElectionContext so we control scenarioMeta directly
vi.mock('../../../stores/useElectionStore', () => ({
  useElection: vi.fn(),
}));

const { useElection } = (await import('../../../stores/useElectionStore')) as unknown as {
  useElection: jest.Mock;
};

const FRANCE2002_META = {
  id: 'france2002',
  name: 'france2002',
  description: 'La gauche fragmentée en 6 candidats élimine Jospin dès le 1er tour.',
  phenomenon: 'Paradoxe de Condorcet',
};

const USA1992_META = {
  id: 'usa1992',
  name: 'usa1992',
  description: 'Perot capture 19% des voix en tant que tiers candidat.',
  phenomenon: 'Effet spoiler',
};

const MOCK_RESULT = {
  config: {},
  voters_snapshot: [],
  candidates: [],
  methods: {
    plurality: {
      winner: 'Chirac',
      bayesian_regret: 0.03,
      majority_satisfaction: 0.7,
      condorcet_consistent: false,
    },
    irv: {
      winner: 'Jospin',
      bayesian_regret: 0.01,
      majority_satisfaction: 0.85,
      condorcet_consistent: true,
    },
    borda: {
      winner: 'Jospin',
      bayesian_regret: 0.01,
      majority_satisfaction: 0.85,
      condorcet_consistent: true,
    },
    schulze: {
      winner: 'Jospin',
      bayesian_regret: 0.01,
      majority_satisfaction: 0.85,
      condorcet_consistent: true,
    },
    approval: {
      winner: 'Jospin',
      bayesian_regret: 0.01,
      majority_satisfaction: 0.85,
      condorcet_consistent: true,
    },
  },
  condorcet_winner: 'Jospin',
  blank_rate: 0,
  campaign_trajectory: null,
  inter_method_agreement: 0.2,
  condorcet_exists: true,
};

function renderPanel(meta: typeof FRANCE2002_META | null, result: any = null) {
  useElection.mockReturnValue({ scenarioMeta: meta, clearScenarioMeta: vi.fn() });
  return render(
    <MemoryRouter>
      <HistoricalReferencePanel result={result} />
    </MemoryRouter>
  );
}

beforeEach(() => vi.clearAllMocks());

describe('HistoricalReferencePanel', () => {
  it('renders nothing when scenarioMeta is null', () => {
    const { container } = renderPanel(null);
    expect(container.firstChild).toBeNull();
  });

  it('renders nothing for an unknown scenario id', () => {
    const unknownMeta = { id: 'unknown_id', name: 'X', description: 'X', phenomenon: 'X' };
    useElection.mockReturnValue({ scenarioMeta: unknownMeta });
    const { container } = render(
      <MemoryRouter>
        <HistoricalReferencePanel result={null} />
      </MemoryRouter>
    );
    expect(container.firstChild).toBeNull();
  });

  it('shows the scenario name (france2002)', () => {
    renderPanel(FRANCE2002_META);
    expect(screen.getByText(/France 2002/i)).toBeInTheDocument();
  });

  it('shows the phenomenon badge', () => {
    renderPanel(FRANCE2002_META);
    // phenomenon may appear multiple times (badge + description) — just check it exists
    expect(screen.getAllByText(/Paradoxe de Condorcet/i).length).toBeGreaterThan(0);
  });

  it('shows the real historical winner (Chirac)', () => {
    renderPanel(FRANCE2002_META);
    // Winner badge + description text — use getAllByText
    expect(screen.getAllByText(/Chirac/i).length).toBeGreaterThan(0);
  });

  it('shows the real result method (scrutin)', () => {
    renderPanel(FRANCE2002_META);
    expect(screen.getAllByText(/Scrutin uninominal/i).length).toBeGreaterThan(0);
  });

  it('shows vote share bars for france2002', () => {
    renderPanel(FRANCE2002_META);
    expect(screen.getAllByText(/1er tour/i).length).toBeGreaterThan(0);
  });

  it('shows usa1992 phenomenon correctly', () => {
    renderPanel(USA1992_META);
    expect(screen.getByText(/USA 1992/i)).toBeInTheDocument();
    expect(screen.getByText(/Effet spoiler/i)).toBeInTheDocument();
  });

  it('shows comparison table header when result is provided', () => {
    renderPanel(FRANCE2002_META, MOCK_RESULT);
    expect(screen.getByText(/Ce que les autres méthodes|What other methods/i)).toBeInTheDocument();
  });

  it('shows Condorcet winner when result has one', () => {
    renderPanel(FRANCE2002_META, MOCK_RESULT);
    // Jospin appears as Condorcet winner + in comparison table winners
    expect(screen.getAllByText(/Jospin/i).length).toBeGreaterThan(0);
  });

  it('shows "no Condorcet winner" when result has none', () => {
    const resultNoCondorcet = { ...MOCK_RESULT, condorcet_winner: null, condorcet_exists: false };
    renderPanel(FRANCE2002_META, resultNoCondorcet);
    expect(screen.getByText(/Pas de vainqueur|No Condorcet/i)).toBeInTheDocument();
  });

  it('shows pedagogical alert when result is provided', () => {
    renderPanel(FRANCE2002_META, MOCK_RESULT);
    // The scenario-specific pedagogical note should appear
    const alerts = document.querySelectorAll('[role="alert"]');
    expect(alerts.length).toBeGreaterThan(0);
  });
});
