import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import BlankVoteDivergencePanel from '../BlankVoteDivergencePanel';
import { ElectionProvider } from '../../../context/ElectionContext';

jest.mock('../../../services/electionApi', () => ({
  fetchDivergence: jest.fn(),
}));

jest.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  BarChart:            ({ children }: any) => <div data-testid="bar-chart">{children}</div>,
  Bar:                 ({ children }: any) => <div>{children}</div>,
  CartesianGrid: () => null,
  Cell:          () => null,
  XAxis:         () => null,
  YAxis:         () => null,
  Tooltip:       () => null,
}));

const { fetchDivergence } = jest.requireMock('../../../services/electionApi') as {
  fetchDivergence: jest.Mock;
};

const MOCK_NO_EFFECT: import('../../../services/electionApi').DivergenceResult = {
  without_blank: {
    methods: {
      plurality: { winner: 'Alice' },
      schulze:   { winner: 'Alice' },
    },
    inter_method_agreement: 1.0,
    condorcet_winner:       'Alice',
  },
  with_blank: {
    methods: {
      plurality: { winner: 'Alice', winner_after_rule: 'Alice' },
      schulze:   { winner: 'Alice', winner_after_rule: 'Alice' },
    },
    inter_method_agreement: 1.0,
    condorcet_winner:       'Alice',
    blank_rate:             0.05,
  },
  delta_agreement:     0.0,
  methods_changed:     [],
  pct_methods_changed: 0.0,
  blank_rule:          'symbolic',
};

const MOCK_HIGH_IMPACT: import('../../../services/electionApi').DivergenceResult = {
  without_blank: {
    methods: {
      plurality: { winner: 'Alice' },
      schulze:   { winner: 'Bob'   },
      borda:     { winner: 'Alice' },
      irv:       { winner: 'Bob'   },
    },
    inter_method_agreement: 0.5,
    condorcet_winner:       'Alice',
  },
  with_blank: {
    methods: {
      plurality: { winner: 'Alice', winner_after_rule: 'Blank'  },
      schulze:   { winner: 'Bob',   winner_after_rule: 'Bob'    },
      borda:     { winner: 'Alice', winner_after_rule: 'Blank'  },
      irv:       { winner: 'Bob',   winner_after_rule: 'Blank'  },
    },
    inter_method_agreement: 0.25,
    condorcet_winner:       null,
    blank_rate:             0.38,
  },
  delta_agreement:     -0.25,
  methods_changed:     ['plurality', 'borda', 'irv'],
  pct_methods_changed: 0.75,
  blank_rule:          'competitive',
};

function renderPanel() {
  return render(
    <MemoryRouter>
      <ElectionProvider>
        <BlankVoteDivergencePanel />
      </ElectionProvider>
    </MemoryRouter>
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
});

describe('BlankVoteDivergencePanel', () => {
  it('renders rule selector and compute button', () => {
    renderPanel();
    expect(screen.getByRole('combobox')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Analyser|Analyse/i })).toBeInTheDocument();
  });

  it('shows prompt when no result loaded', () => {
    renderPanel();
    expect(screen.getByText(/Choisissez|Choose/i)).toBeInTheDocument();
  });

  it('calls fetchDivergence when compute button clicked', async () => {
    fetchDivergence.mockResolvedValue(MOCK_NO_EFFECT);
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /Analyser|Analyse/i }));
    await waitFor(() => expect(fetchDivergence).toHaveBeenCalledTimes(1));
  });

  it('displays two columns after result loads', async () => {
    fetchDivergence.mockResolvedValue(MOCK_NO_EFFECT);
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /Analyser|Analyse/i }));
    await waitFor(() => {
      expect(screen.getByText(/Sans vote blanc|Without blank/i)).toBeInTheDocument();
      expect(screen.getByText(/Avec vote blanc|With blank/i)).toBeInTheDocument();
    });
  });

  it('shows green delta badge when no effect (delta = 0)', async () => {
    fetchDivergence.mockResolvedValue(MOCK_NO_EFFECT);
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /Analyser|Analyse/i }));
    // No-impact message should appear
    await waitFor(() => {
      expect(screen.getByText(/n'a pas modifié|did not change/i)).toBeInTheDocument();
    });
  });

  it('shows red delta badge when high impact (delta < -0.05)', async () => {
    fetchDivergence.mockResolvedValue(MOCK_HIGH_IMPACT);
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /Analyser|Analyse/i }));
    await waitFor(() => {
      // High impact message should appear
      expect(screen.getByText(/modifie le vainqueur|changes the winner/i)).toBeInTheDocument();
    });
  });

  it('shows bar chart when result is available', async () => {
    fetchDivergence.mockResolvedValue(MOCK_NO_EFFECT);
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /Analyser|Analyse/i }));
    await waitFor(() => {
      expect(screen.getByTestId('bar-chart')).toBeInTheDocument();
    });
  });

  it('passes the selected rule to fetchDivergence', async () => {
    fetchDivergence.mockResolvedValue(MOCK_NO_EFFECT);
    renderPanel();
    const select = screen.getByRole('combobox');
    fireEvent.change(select, { target: { value: 'competitive' } });
    fireEvent.click(screen.getByRole('button', { name: /Analyser|Analyse/i }));
    await waitFor(() => {
      const params = fetchDivergence.mock.calls[0][0];
      expect(params.blank_vote.rule).toBe('competitive');
    });
  });
});
