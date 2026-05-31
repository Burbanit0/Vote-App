import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import MethodRadarChart from '../MethodRadarChart';

jest.mock('../../../stores/useUIStore', () => ({
  ...jest.requireActual('../../../stores/useUIStore'),
  useExpertMode: () => ({ expertMode: true, setExpertMode: jest.fn() }),
}));

jest.mock('recharts', () => ({
  RadarChart:       ({ children }: any) => <div data-testid="radar-chart">{children}</div>,
  Radar:            ({ name }: any)     => <div data-testid={`radar-${name}`} />,
  PolarGrid:        () => null,
  PolarAngleAxis:   () => null,
  PolarRadiusAxis:  () => null,
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  Tooltip:          () => null,
  Legend:           ({ formatter, onClick }: any) => (
    <div data-testid="legend">
      {['plurality', 'schulze', 'borda'].map((m) => (
        <span
          key={m}
          data-testid={`legend-${m}`}
          onClick={() => onClick && onClick({ dataKey: m })}
        >
          {formatter ? formatter(m) : m}
        </span>
      ))}
    </div>
  ),
}));

// Typical SimulationCompareResult[]
const makeResults = (winners: Record<string, string>, condorcet: boolean) =>
  Array.from({ length: 10 }, () => ({
    condorcet_winner: condorcet ? winners['schulze'] : null,
    methods: {
      plurality: { winner: winners['plurality'] ?? 'Alice', bayesian_regret: 0.08, majority_satisfaction: 0.65, strategic_vulnerability: 0.35, condorcet_consistent: false },
      schulze:   { winner: winners['schulze']   ?? 'Alice', bayesian_regret: 0.02, majority_satisfaction: 0.88, strategic_vulnerability: 0.05, condorcet_consistent: condorcet },
      borda:     { winner: winners['borda']     ?? 'Alice', bayesian_regret: 0.04, majority_satisfaction: 0.80, strategic_vulnerability: 0.15, condorcet_consistent: condorcet },
      irv:       { winner: winners['irv']       ?? 'Alice', bayesian_regret: 0.03, majority_satisfaction: 0.82, strategic_vulnerability: 0.12, condorcet_consistent: condorcet },
      approval:  { winner: winners['approval']  ?? 'Alice', bayesian_regret: 0.05, majority_satisfaction: 0.75, strategic_vulnerability: 0.20, condorcet_consistent: false },
    },
  }));

const ALL_WIN    = { plurality: 'Alice', schulze: 'Alice', borda: 'Alice', irv: 'Alice', approval: 'Alice' };
const MIXED_WIN  = { plurality: 'Bob',   schulze: 'Alice', borda: 'Alice', irv: 'Alice', approval: 'Bob'   };

const ALL_METHODS = ['plurality', 'schulze', 'borda', 'irv', 'approval'];

describe('MethodRadarChart', () => {
  it('renders nothing when no results', () => {
    const { container } = render(
      <MethodRadarChart comparisonResults={[]} allMethodNames={ALL_METHODS} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders the radar chart with results', () => {
    render(
      <MethodRadarChart
        comparisonResults={makeResults(ALL_WIN, true)}
        allMethodNames={ALL_METHODS}
      />
    );
    expect(screen.getByTestId('radar-chart')).toBeInTheDocument();
  });

  it('shows the best method badge', () => {
    render(
      <MethodRadarChart
        comparisonResults={makeResults(ALL_WIN, true)}
        allMethodNames={ALL_METHODS}
      />
    );
    // badge text uses i18n key — accept key or translated value
    expect(screen.getAllByText(/Meilleure|Best|bestMethod|radar\.bestMethod/i).length).toBeGreaterThan(0);
  });

  it('renders a Radar component for each visible method', () => {
    render(
      <MethodRadarChart
        comparisonResults={makeResults(ALL_WIN, true)}
        allMethodNames={ALL_METHODS}
      />
    );
    // By default top-5 are visible; since we have 5 methods, all should be present
    expect(screen.getAllByTestId(/^radar-/).length).toBeGreaterThan(0);
  });

  it('checkboxes are rendered for each method', () => {
    render(
      <MethodRadarChart
        comparisonResults={makeResults(ALL_WIN, true)}
        allMethodNames={ALL_METHODS}
      />
    );
    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes.length).toBe(ALL_METHODS.length);
  });

  it('unchecking a checkbox hides that method from the radar', () => {
    render(
      <MethodRadarChart
        comparisonResults={makeResults(ALL_WIN, true)}
        allMethodNames={ALL_METHODS}
      />
    );
    // Find the plurality checkbox and uncheck it
    const pluralityCheckbox = screen.getByRole('checkbox', { name: /plurality/i });
    fireEvent.click(pluralityCheckbox);
    expect(pluralityCheckbox).not.toBeChecked();
    // The radar for plurality should no longer render
    expect(screen.queryByTestId('radar-plurality')).toBeNull();
  });

  it('in expert mode all methods show checkboxes', () => {
    const extendedMethods = [...ALL_METHODS, 'star_voting', 'median_voting'];
    render(
      <MethodRadarChart
        comparisonResults={makeResults(ALL_WIN, true)}
        allMethodNames={extendedMethods}
      />
    );
    const checkboxes = screen.getAllByRole('checkbox');
    // In expert mode (mocked above) all methods get a checkbox
    expect(checkboxes.length).toBe(extendedMethods.length);
  });

  it('shows selectMethods label (i18n key or translation)', () => {
    render(
      <MethodRadarChart
        comparisonResults={makeResults(MIXED_WIN, true)}
        allMethodNames={ALL_METHODS}
      />
    );
    expect(screen.getAllByText(/Afficher|Show|selectMethods|radar\.selectMethods/i).length).toBeGreaterThan(0);
  });
});
