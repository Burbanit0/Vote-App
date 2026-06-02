import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import CombinedEffectsMatrix from '../CombinedEffectsMatrix';
import { ElectionProvider } from '../../../stores/useElectionStore';

vi.mock('../../../services/electionApi', () => ({
  fetchCombinedEffects: vi.fn(),
}));

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  BarChart:            ({ children }: any) => <div data-testid="bar-chart">{children}</div>,
  Bar:                 ({ children }: any) => <div>{children}</div>,
  CartesianGrid: () => null,
  Cell:          () => null,
  LabelList:     () => null,
  XAxis:         () => null,
  YAxis:         () => null,
  Tooltip:       () => null,
}));

const { fetchCombinedEffects } = (await import('../../../services/electionApi')) as unknown as {
  fetchCombinedEffects: jest.Mock;
};

// 8 combinations: blank × campaign × info
function makeCombination(blank: boolean, campaign: boolean, info: boolean, winner: string, agree: number) {
  return {
    id:                     `blank=${blank ? 'on' : 'off'},campaign=${campaign ? 'on' : 'off'},info=${info ? 'on' : 'off'}`,
    blank,
    campaign,
    information_model:      info,
    plurality_winner:       winner,
    condorcet_winner:       winner,
    inter_method_agreement: agree,
    winner_differs_from_base: winner !== 'Alice',
  };
}

const MOCK_RESULT = {
  base_winner:  'Alice',
  combinations: [
    makeCombination(false, false, false, 'Alice', 0.90),
    makeCombination(false, false, true,  'Alice', 0.85),
    makeCombination(false, true,  false, 'Alice', 0.80),
    makeCombination(false, true,  true,  'Bob',   0.70),
    makeCombination(true,  false, false, 'Alice', 0.75),
    makeCombination(true,  false, true,  'Bob',   0.65),
    makeCombination(true,  true,  false, 'Bob',   0.55),
    makeCombination(true,  true,  true,  'Bob',   0.42),
  ],
  factor_deltas:             { blank: -14.0, campaign: -8.0, information_model: -5.0 },
  most_disruptive_factor:    'blank',
  least_disruptive_factor:   'information_model',
  max_disruption_combination: 'blank=on,campaign=on,info=on',
};

function renderPanel() {
  return render(
    <MemoryRouter>
      <ElectionProvider>
        <CombinedEffectsMatrix />
      </ElectionProvider>
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  fetchCombinedEffects.mockResolvedValue(MOCK_RESULT);
});

describe('CombinedEffectsMatrix', () => {
  it('renders the compute button', () => {
    renderPanel();
    expect(screen.getByRole('button', { name: /Analyser|Analyse/i })).toBeInTheDocument();
  });

  it('shows prompt before analysis', () => {
    renderPanel();
    expect(screen.getByText(/Cliquez|Click/i)).toBeInTheDocument();
  });

  it('calls fetchCombinedEffects when button clicked', async () => {
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /Analyser|Analyse/i }));
    await waitFor(() => expect(fetchCombinedEffects).toHaveBeenCalledTimes(1));
  });

  it('renders the matrix table after analysis', async () => {
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /Analyser|Analyse/i }));
    await waitFor(() => {
      expect(screen.getByRole('table')).toBeInTheDocument();
    });
  });

  it('each winner name appears in the matrix', async () => {
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /Analyser|Analyse/i }));
    await waitFor(() => {
      // Alice and Bob both appear (multiple times as matrix cells)
      const aliceCells = screen.getAllByText(/Alice/);
      const bobCells   = screen.getAllByText(/Bob/);
      expect(aliceCells.length).toBeGreaterThan(0);
      expect(bobCells.length).toBeGreaterThan(0);
    });
  });

  it('renders the factor contribution bar chart', async () => {
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /Analyser|Analyse/i }));
    await waitFor(() => {
      expect(screen.getByTestId('bar-chart')).toBeInTheDocument();
    });
  });

  it('shows synthesis text with most disruptive factor', async () => {
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /Analyser|Analyse/i }));
    await waitFor(() => {
      // The synthesis card should contain text about blank being disruptive
      const badges = screen.getAllByText(/blank|Vote blanc/i);
      expect(badges.length).toBeGreaterThan(0);
    });
  });

  it('shows most and least disruptive badges', async () => {
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /Analyser|Analyse/i }));
    await waitFor(() => {
      // Badges contain the factor key names
      const disruptiveBadges = screen.getAllByText(/disruptif|disruptive/i);
      expect(disruptiveBadges.length).toBeGreaterThan(0);
    });
  });
});
