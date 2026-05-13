import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import RealElectionsTab from '../RealElectionsTab';
import { getRealElections, analyzeRealElection } from '../../../services/simulationCompareApi';

jest.mock('../../../services/simulationCompareApi', () => ({
  getRealElections: jest.fn(),
  analyzeRealElection: jest.fn(),
}));

jest.mock('../RealElectionAnalysis', () => () => <div data-testid="real-election-analysis" />);

const mockElections = [
  { key: 'fr-2022', name: 'Présidentielle 2022', year: 2022, country: 'France' },
  { key: 'us-2020', name: 'Presidential 2020', year: 2020, country: 'USA' },
];

const mockResult = {
  election: { key: 'fr-2022', name: 'Présidentielle 2022', year: 2022, country: 'France', description: '', source: '', candidates: [], estimated_blank_pct: 5 },
  plurality_winner: 'A',
  first_round_results: { A: 30, B: 25 },
  methods: { plurality: 'A', irv: 'B' },
  divergences: [],
  summary: { methods_with_different_winner: 1, total_methods_with_winner: 2 },
};

describe('RealElectionsTab', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (getRealElections as jest.Mock).mockResolvedValue(mockElections);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('loads election list on mount', async () => {
    render(<RealElectionsTab />);
    await waitFor(() => {
      expect(getRealElections).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(screen.getByText(/Présidentielle 2022/)).toBeInTheDocument();
    });
  });

  it('shows info alert before analysis', async () => {
    render(<RealElectionsTab />);
    await waitFor(() => {
      expect(screen.getByText(/Sélectionnez une élection/)).toBeInTheDocument();
    });
  });

  it('renders analysis on button click', async () => {
    (analyzeRealElection as jest.Mock).mockResolvedValue(mockResult);
    render(<RealElectionsTab />);

    await waitFor(() => {
      expect(screen.getByText(/Présidentielle 2022/)).toBeInTheDocument();
    });

    const buttons = screen.getAllByText('Analyser');
    const analyseButton = buttons.find((btn) => btn.tagName === 'BUTTON' || btn.closest('button'));
    fireEvent.click(analyseButton || buttons[0]);

    await waitFor(() => {
      expect(analyzeRealElection).toHaveBeenCalledWith('fr-2022', 1000, false);
    });
    await waitFor(() => {
      expect(screen.getByTestId('real-election-analysis')).toBeInTheDocument();
    });
  });

  it('shows loading state during analysis', async () => {
    (analyzeRealElection as jest.Mock).mockReturnValue(new Promise(() => {}));
    render(<RealElectionsTab />);

    await waitFor(() => {
      expect(screen.getByText(/Présidentielle 2022/)).toBeInTheDocument();
    });

    const buttons = screen.getAllByText('Analyser');
    const analyseButton = buttons.find((btn) => btn.tagName === 'BUTTON' || btn.closest('button'));
    fireEvent.click(analyseButton || buttons[0]);

    await waitFor(() => {
      expect(screen.getByText(/Analyse…/)).toBeInTheDocument();
    });
  });
});
