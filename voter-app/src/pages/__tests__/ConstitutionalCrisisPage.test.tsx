import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ConstitutionalCrisisPage from '../ConstitutionalCrisisPage';

jest.mock('../../components/ScenarioBuilder/CandidateEditor', () => {
  const MockCandidateEditor: React.FC = () => (
    <div data-testid="candidate-editor">CandidateEditor</div>
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

jest.mock('../../components/ConstitutionalCrisis/ScenarioAPanel', () => {
  return function MockScenarioAPanel({ onRun }: { onRun: (candidates: unknown[]) => void }) {
    return (
      <div data-testid="scenario-a-panel">
        <button onClick={() => onRun([])}>Run A</button>
      </div>
    );
  };
});

jest.mock('../../components/ConstitutionalCrisis/ScenarioBPanel', () => {
  return function MockScenarioBPanel({ onRun }: { onRun: (duration: number, drift: number) => void }) {
    return (
      <div data-testid="scenario-b-panel">
        <button onClick={() => onRun(3, 0.05)}>Run B</button>
      </div>
    );
  };
});

jest.mock('../../components/ConstitutionalCrisis/ScenarioCPanel', () => {
  return function MockScenarioCPanel({ onRun }: { onRun: (seats: number) => void }) {
    return (
      <div data-testid="scenario-c-panel">
        <button onClick={() => onRun(30)}>Run C</button>
      </div>
    );
  };
});

jest.mock('../../services/simulationCompareApi', () => ({
  runScenario: jest.fn(),
  runConstitutionalScenario: jest.fn(),
}));

jest.mock('../../components/shared/ToastNotification', () => ({
  useToast: () => ({ error: jest.fn() }),
}));

const { runScenario } = require('../../services/simulationCompareApi');
const { runConstitutionalScenario } = require('../../services/simulationCompareApi');

describe('ConstitutionalCrisisPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders the page title', () => {
    render(<ConstitutionalCrisisPage />);
    expect(screen.getByText('Simulateur de crise constitutionnelle')).toBeInTheDocument();
  });

  it('shows CandidateEditor and ElectorateConfig', () => {
    render(<ConstitutionalCrisisPage />);
    expect(screen.getByTestId('candidate-editor')).toBeInTheDocument();
    expect(screen.getByTestId('electorate-config')).toBeInTheDocument();
  });

  it('shows info alert before initial simulation', () => {
    render(<ConstitutionalCrisisPage />);
    expect(screen.getByText(/Configurez l'élection/)).toBeInTheDocument();
  });

  it('calls runScenario when simulate button is clicked', async () => {
    (runScenario as jest.Mock).mockResolvedValue({
      without_blank: { methods: { plurality: { winner: 'Alice' } }, condorcet_winner: 'Alice' },
      with_blank: { blank_pct: 0.3, methods: { plurality: { winner: 'Blank', blank_rule_applied: { blank_triggered: true } } } },
    });

    render(<ConstitutionalCrisisPage />);
    fireEvent.click(screen.getByRole('button', { name: /Simuler/ }));

    await waitFor(() => {
      expect(runScenario).toHaveBeenCalledTimes(1);
    });
  });

  it('shows blank wins banner when blank vote triggers', async () => {
    (runScenario as jest.Mock).mockResolvedValue({
      without_blank: { methods: { plurality: { winner: 'Alice' } }, condorcet_winner: 'Alice' },
      with_blank: { blank_pct: 0.4, methods: { plurality: { winner: 'Blank', blank_rule_applied: { blank_triggered: true } } } },
    });

    render(<ConstitutionalCrisisPage />);
    fireEvent.click(screen.getByRole('button', { name: /Simuler/ }));

    await waitFor(() => {
      expect(screen.getByText(/Vote blanc victorieux/)).toBeInTheDocument();
    });
  });

  it('shows scenario tabs when blank wins', async () => {
    (runScenario as jest.Mock).mockResolvedValue({
      without_blank: { methods: { plurality: { winner: 'Alice' } }, condorcet_winner: 'Alice' },
      with_blank: { blank_pct: 0.4, methods: { plurality: { winner: 'Blank', blank_rule_applied: { blank_triggered: true } } } },
    });

    render(<ConstitutionalCrisisPage />);
    fireEvent.click(screen.getByRole('button', { name: /Simuler/ }));

    await waitFor(() => {
      expect(screen.getByText(/Nouvelle élection/)).toBeInTheDocument();
      expect(screen.getByText(/Gouvernement provisoire/)).toBeInTheDocument();
      expect(screen.getByText(/Dissolution proportionnelle/)).toBeInTheDocument();
    });
  });
});
