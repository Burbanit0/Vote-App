import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ConstitutionalCrisisPage from '../ConstitutionalCrisisPage';

vi.mock('../../components/ScenarioBuilder/CandidateEditor', () => {
  const MockCandidateEditor: React.FC = () => (
    <div data-testid="candidate-editor">CandidateEditor</div>
  );
  return {
    __esModule: true,
    default: MockCandidateEditor,
    newCandidate: (name: string, ideology: number) => ({
      name,
      ideology,
      economy: 0.5,
      environment: 0.5,
      social: 0.5,
      isBlank: false,
    }),
    newBlankCandidate: () => ({
      name: 'Blanc',
      ideology: 0,
      economy: 0.5,
      environment: 0.5,
      social: 0.5,
      isBlank: true,
    }),
  };
});

vi.mock('../../components/ScenarioBuilder/ElectorateConfig', () => {
  return {
    default: function MockElectorateConfig() {
      return <div data-testid="electorate-config">ElectorateConfig</div>;
    },
  };
});

vi.mock('../../components/ConstitutionalCrisis/ScenarioAPanel', () => {
  return {
    default: function MockScenarioAPanel({ onRun }: { onRun: (candidates: unknown[]) => void }) {
      return (
        <div data-testid="scenario-a-panel">
          <button onClick={() => onRun([])}>Run A</button>
        </div>
      );
    },
  };
});

vi.mock('../../components/ConstitutionalCrisis/ScenarioBPanel', () => {
  return {
    default: function MockScenarioBPanel({
      onRun,
    }: {
      onRun: (duration: number, drift: number) => void;
    }) {
      return (
        <div data-testid="scenario-b-panel">
          <button onClick={() => onRun(3, 0.05)}>Run B</button>
        </div>
      );
    },
  };
});

vi.mock('../../components/ConstitutionalCrisis/ScenarioCPanel', () => {
  return {
    default: function MockScenarioCPanel({ onRun }: { onRun: (seats: number) => void }) {
      return (
        <div data-testid="scenario-c-panel">
          <button onClick={() => onRun(30)}>Run C</button>
        </div>
      );
    },
  };
});

vi.mock('../../services/simulationCompareApi', () => ({
  runScenario: vi.fn(),
  runConstitutionalScenario: vi.fn(),
}));

vi.mock('../../components/shared/ToastNotification', () => ({
  useToast: () => ({ error: vi.fn() }),
}));

const { runScenario } = await import('../../services/simulationCompareApi');
const { runConstitutionalScenario } = await import('../../services/simulationCompareApi');

describe('ConstitutionalCrisisPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the page title', () => {
    render(<ConstitutionalCrisisPage />);
    expect(screen.getByText('Constitutional crisis simulator')).toBeInTheDocument();
  });

  it('shows CandidateEditor and ElectorateConfig', () => {
    render(<ConstitutionalCrisisPage />);
    expect(screen.getByTestId('candidate-editor')).toBeInTheDocument();
    expect(screen.getByTestId('electorate-config')).toBeInTheDocument();
  });

  it('shows info alert before initial simulation', () => {
    render(<ConstitutionalCrisisPage />);
    expect(screen.getByText(/Configure the election/)).toBeInTheDocument();
  });

  it('calls runScenario when simulate button is clicked', async () => {
    (runScenario as jest.Mock).mockResolvedValue({
      without_blank: { methods: { plurality: { winner: 'Alice' } }, condorcet_winner: 'Alice' },
      with_blank: {
        blank_pct: 0.3,
        methods: { plurality: { winner: 'Blank', blank_rule_applied: { blank_triggered: true } } },
      },
    });

    render(<ConstitutionalCrisisPage />);
    fireEvent.click(screen.getByRole('button', { name: /Simulate/ }));

    await waitFor(() => {
      expect(runScenario).toHaveBeenCalledTimes(1);
    });
  });

  it('shows blank wins banner when blank vote triggers', async () => {
    (runScenario as jest.Mock).mockResolvedValue({
      without_blank: { methods: { plurality: { winner: 'Alice' } }, condorcet_winner: 'Alice' },
      with_blank: {
        blank_pct: 0.4,
        methods: { plurality: { winner: 'Blank', blank_rule_applied: { blank_triggered: true } } },
      },
    });

    render(<ConstitutionalCrisisPage />);
    fireEvent.click(screen.getByRole('button', { name: /Simulate/ }));

    await waitFor(() => {
      expect(screen.getByText(/Blank vote wins/)).toBeInTheDocument();
    });
  });

  it('shows scenario tabs when blank wins', async () => {
    (runScenario as jest.Mock).mockResolvedValue({
      without_blank: { methods: { plurality: { winner: 'Alice' } }, condorcet_winner: 'Alice' },
      with_blank: {
        blank_pct: 0.4,
        methods: { plurality: { winner: 'Blank', blank_rule_applied: { blank_triggered: true } } },
      },
    });

    render(<ConstitutionalCrisisPage />);
    fireEvent.click(screen.getByRole('button', { name: /Simulate/ }));

    await waitFor(() => {
      expect(screen.getByText(/New election/)).toBeInTheDocument();
      expect(screen.getByText(/Provisional government/)).toBeInTheDocument();
      expect(screen.getByText(/Proportional dissolution/)).toBeInTheDocument();
    });
  });
});
