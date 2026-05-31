import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import ArrowExplorer from '../ArrowExplorer';
import { makeTestQueryClient } from '../../../test/queryWrapper';

jest.mock('../../../api/client', () => ({
  apiClient: { GET: jest.fn(), POST: jest.fn(), PUT: jest.fn(), DELETE: jest.fn(), PATCH: jest.fn() },
  getAccessToken: jest.fn(() => null),
}));
const { apiClient } = jest.requireMock('../../../api/client') as { apiClient: { POST: jest.Mock } };

jest.mock('recharts', () => {
  const React = require('react');
  return {
    LineChart:           ({ children }: any) => <div>{children}</div>,
    Line:                ({ dataKey }: any) => <div data-testid={`line-${dataKey}`} />,
    XAxis:               () => null,
    YAxis:               () => null,
    CartesianGrid:       () => null,
    Tooltip:             () => null,
    Legend:              () => null,
    ReferenceLine:       () => null,
    ResponsiveContainer: ({ children }: any) => <div style={{ width: 400, height: 200 }}>{children}</div>,
  };
});

// ── Fixtures ──────────────────────────────────────────────────────────────────

function makeArrowData(method = 'plurality') {
  return {
    data: {
      method,
      violations: {
        iia:              { violated: true, counterexample: {
          profile: [['A','C','B'],['A','C','B'],['A','C','B'],['B','A','C'],['B','A','C'],['C','B','A'],['C','B','A']],
          without_c: 'B', with_c: 'A', spoiler: 'C', note: 'Test note.',
        }},
        pareto:           { violated: false, counterexample: null },
        transitivity:     { violated: false, counterexample: null },
        non_dictatorship: { violated: false, counterexample: null },
      },
      arrow_summary: 'Test summary.',
      tradeoff_type: 'majority_focus',
    },
    error: undefined,
  };
}

function makeRateData(method = 'plurality') {
  return {
    data: {
      method,
      curve: [
        { n_candidates: 2, violation_rate: 0.0 },
        { n_candidates: 3, violation_rate: 0.45 },
        { n_candidates: 4, violation_rate: 0.58 },
        { n_candidates: 5, violation_rate: 0.65 },
      ],
    },
    error: undefined,
  };
}

function renderExplorer() {
  return render(
    <MemoryRouter>
      <QueryClientProvider client={makeTestQueryClient()}>
        <ArrowExplorer />
      </QueryClientProvider>
    </MemoryRouter>
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  jest.useFakeTimers();
});

afterEach(() => { jest.useRealTimers(); });

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('ArrowExplorer', () => {
  it('shows analyze button', () => {
    renderExplorer();
    expect(screen.getByTestId('analyze-btn')).toBeInTheDocument();
  });

  it('shows method selector', () => {
    renderExplorer();
    expect(screen.getByTestId('method-select')).toBeInTheDocument();
  });

  it('shows axiom filter checkboxes', () => {
    renderExplorer();
    expect(screen.getByTestId('axiom-check-iia')).toBeInTheDocument();
    expect(screen.getByTestId('axiom-check-pareto')).toBeInTheDocument();
    expect(screen.getByTestId('axiom-check-transitivity')).toBeInTheDocument();
    expect(screen.getByTestId('axiom-check-non_dictatorship')).toBeInTheDocument();
  });

  it('shows axiom filter section', () => {
    renderExplorer();
    expect(screen.getByTestId('axiom-filter-section')).toBeInTheDocument();
  });

  it('calls both API endpoints on analyze click', async () => {
    apiClient.POST
      .mockResolvedValueOnce(makeArrowData())
      .mockResolvedValueOnce(makeRateData());
    renderExplorer();
    fireEvent.click(screen.getByTestId('analyze-btn'));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(2));
    expect(apiClient.POST).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/(v2\/)?theory\/arrow/),
      expect.any(Object),
    );
    expect(apiClient.POST).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/(v2\/)?theory\/iia-rate/),
      expect.any(Object),
    );
    jest.runAllTimers();
  });

  it('renders pentagon SVG after analysis', async () => {
    apiClient.POST.mockResolvedValueOnce(makeArrowData()).mockResolvedValueOnce(makeRateData());
    renderExplorer();
    fireEvent.click(screen.getByTestId('analyze-btn'));
    await waitFor(() => expect(screen.getByTestId('arrow-pentagon')).toBeInTheDocument(), { timeout: 8000 });
    jest.runAllTimers();
  });

  it('shows counterexample card for IIA', async () => {
    apiClient.POST.mockResolvedValueOnce(makeArrowData()).mockResolvedValueOnce(makeRateData());
    renderExplorer();
    fireEvent.click(screen.getByTestId('analyze-btn'));
    await waitFor(() => expect(screen.getByTestId('counterexample-iia')).toBeInTheDocument(), { timeout: 8000 });
    jest.runAllTimers();
  });

  it('shows IIA rate chart after analysis', async () => {
    apiClient.POST.mockResolvedValueOnce(makeArrowData()).mockResolvedValueOnce(makeRateData());
    renderExplorer();
    fireEvent.click(screen.getByTestId('analyze-btn'));
    await waitFor(() => expect(screen.getByTestId('iia-rate-chart')).toBeInTheDocument(), { timeout: 8000 });
    jest.runAllTimers();
  });

  it('shows axiom comparison matrix', () => {
    renderExplorer();
    expect(screen.getByTestId('axiom-matrix')).toBeInTheDocument();
  });

  it('shows compatible-methods when axioms are checked', () => {
    renderExplorer();
    // Check one axiom
    fireEvent.click(screen.getByTestId('axiom-check-iia'));
    expect(screen.getByTestId('compatible-methods')).toBeInTheDocument();
  });

  it('shows Arrow impossibility message when all axioms checked', () => {
    renderExplorer();
    // Check all axioms
    ['iia', 'pareto', 'transitivity', 'non_dictatorship'].forEach((ax) => {
      fireEvent.click(screen.getByTestId(`axiom-check-${ax}`));
    });
    expect(screen.getByTestId('compatible-methods')).toBeInTheDocument();
  });

  it('shows error on API failure', async () => {
    apiClient.POST.mockRejectedValue(new Error('Network error'));
    renderExplorer();
    fireEvent.click(screen.getByTestId('analyze-btn'));
    await waitFor(() => expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument());
  });
});
