import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ScenarioBuilderPage from '../ScenarioBuilderPage';

jest.mock('../../components/ScenarioBuilder/CandidateEditor', () => {
  const MockCandidateEditor: React.FC<{ candidates: { name: string; isBlank?: boolean }[] }> = ({ candidates }) => (
    <div data-testid="candidate-editor">
      {candidates.map((c, i) => (
        <span key={i}>{c.name}{c.isBlank ? ' (blank)' : ''}</span>
      ))}
    </div>
  );
  return {
    __esModule: true,
    default: MockCandidateEditor,
    newCandidate: (name: string, ideology: number) => ({
      name, ideology, economy: 0.5, environment: 0.5, social: 0.5, isBlank: false,
    }),
    newBlankCandidate: () => ({
      name: 'Blanc', ideology: 0, economy: 0.5, environment: 0.5, social: 0.5, isBlank: true,
    }),
  };
});

jest.mock('../../components/ScenarioBuilder/ElectorateConfig', () => {
  return function MockElectorateConfig() {
    return <div data-testid="electorate-config">ElectorateConfig</div>;
  };
});

jest.mock('../../components/ScenarioBuilder/BlankVoteRuleSelector', () => {
  return function MockBlankVoteRuleSelector() {
    return <div data-testid="blank-rule-selector">BlankVoteRuleSelector</div>;
  };
});

jest.mock('../../services/simulationCompareApi', () => ({
  runScenario: jest.fn(),
}));

jest.mock('../../utils/shareUtils', () => ({
  buildShareURL: jest.fn(() => 'http://example.com/share'),
  copyShareURL: jest.fn(),
  decodeShareConfig: jest.fn(),
  readShareParam: jest.fn(() => null),
}));

jest.mock('../../components/shared/ToastNotification', () => ({
  useToast: () => ({ error: jest.fn() }),
}));

jest.mock('../../stores/useUIStore', () => ({
  ...jest.requireActual('../../stores/useUIStore'),
  useExpertMode: () => ({ expertMode: false }),
}));

jest.mock('../../hooks/useMetaTags', () => ({
  useMetaTags: jest.fn(),
}));

const { runScenario } = require('../../services/simulationCompareApi');

describe('ScenarioBuilderPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders the page title and step indicator', () => {
    render(<ScenarioBuilderPage />);
    expect(screen.getByText('Election scenario builder')).toBeInTheDocument();
    expect(screen.getAllByText('Candidates').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Electorate').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Blank vote rule').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Results').length).toBeGreaterThanOrEqual(1);
  });

  it('shows CandidateEditor on step 0', () => {
    render(<ScenarioBuilderPage />);
    expect(screen.getByTestId('candidate-editor')).toBeInTheDocument();
  });

  it('shows ElectorateConfig after clicking Next', () => {
    render(<ScenarioBuilderPage />);
    fireEvent.click(screen.getByText('Next →'));
    expect(screen.getByTestId('electorate-config')).toBeInTheDocument();
  });

  it('shows BlankVoteRuleSelector after second Next', () => {
    render(<ScenarioBuilderPage />);
    fireEvent.click(screen.getByText('Next →'));
    fireEvent.click(screen.getByText('Next →'));
    expect(screen.getByTestId('blank-rule-selector')).toBeInTheDocument();
  });

  it('calls runScenario and shows results on step 2 click', async () => {
    const mockResult = {
      without_blank: {
        methods: { plurality: { winner: 'Alice' }, irv: { winner: 'Bob' } },
        condorcet_winner: 'Alice',
      },
      with_blank: {
        blank_pct: 0.15,
        methods: {
          plurality: { winner: 'Alice', blank_rule_applied: null },
          irv: { winner: 'Bob', blank_rule_applied: null },
        },
      },
    };
    (runScenario as jest.Mock).mockResolvedValue(mockResult);

    render(<ScenarioBuilderPage />);
    fireEvent.click(screen.getByText('Next →'));
    fireEvent.click(screen.getByText('Next →'));
    fireEvent.click(screen.getByText('▶ Run simulation'));

    await waitFor(() => {
      expect(runScenario).toHaveBeenCalledTimes(1);
    });
    await waitFor(() => {
      expect(screen.getAllByText(/15/).length).toBeGreaterThanOrEqual(1);
    });
  });

  it('does not show candidate warning when 2+ real candidates exist', () => {
    render(<ScenarioBuilderPage />);
    expect(screen.queryByText(/Add at least 2 real candidates/)).toBeNull();
  });

  it('allows going back to previous step', () => {
    render(<ScenarioBuilderPage />);
    fireEvent.click(screen.getByText('Next →'));
    expect(screen.getByTestId('electorate-config')).toBeInTheDocument();
    fireEvent.click(screen.getByText('← Back'));
    expect(screen.getByTestId('candidate-editor')).toBeInTheDocument();
  });
});
