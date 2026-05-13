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

jest.mock('../../context/ExpertModeContext', () => ({
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
    expect(screen.getByText('Constructeur de scénario électoral')).toBeInTheDocument();
    expect(screen.getAllByText('Candidats').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Électorat').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Règle vote blanc').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Résultats').length).toBeGreaterThanOrEqual(1);
  });

  it('shows CandidateEditor on step 0', () => {
    render(<ScenarioBuilderPage />);
    expect(screen.getByTestId('candidate-editor')).toBeInTheDocument();
  });

  it('shows ElectorateConfig after clicking Suivant', () => {
    render(<ScenarioBuilderPage />);
    fireEvent.click(screen.getByText('Suivant →'));
    expect(screen.getByTestId('electorate-config')).toBeInTheDocument();
  });

  it('shows BlankVoteRuleSelector after second Suivant', () => {
    render(<ScenarioBuilderPage />);
    fireEvent.click(screen.getByText('Suivant →'));
    fireEvent.click(screen.getByText('Suivant →'));
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
    fireEvent.click(screen.getByText('Suivant →'));
    fireEvent.click(screen.getByText('Suivant →'));
    fireEvent.click(screen.getByText('▶ Lancer la simulation'));

    await waitFor(() => {
      expect(runScenario).toHaveBeenCalledTimes(1);
    });
    await waitFor(() => {
      expect(screen.getAllByText(/15/).length).toBeGreaterThanOrEqual(1);
    });
  });

  it('does not show candidate warning when 2+ real candidates exist', () => {
    render(<ScenarioBuilderPage />);
    expect(screen.queryByText(/Ajoutez au moins 2 candidats réels/)).toBeNull();
  });

  it('allows going back to previous step', () => {
    render(<ScenarioBuilderPage />);
    fireEvent.click(screen.getByText('Suivant →'));
    expect(screen.getByTestId('electorate-config')).toBeInTheDocument();
    fireEvent.click(screen.getByText('← Retour'));
    expect(screen.getByTestId('candidate-editor')).toBeInTheDocument();
  });
});
