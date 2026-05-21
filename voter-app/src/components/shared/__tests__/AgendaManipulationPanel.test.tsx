import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import axios from 'axios';
import AgendaManipulationPanel from '../AgendaManipulationPanel';

jest.mock('axios');
const mockAxios = axios as jest.Mocked<typeof axios>;

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, string>) => {
      if (opts?.target) return `Make ${opts.target} win`;
      return key.split('.').pop() ?? key;
    },
  }),
}));

const MOCK_DATA = {
  pairwise_matrix: {
    Alice: { Alice: 0.5, Bob: 0.7, Carol: 0.6 },
    Bob:   { Alice: 0.3, Bob: 0.5, Carol: 0.4 },
    Carol: { Alice: 0.4, Bob: 0.6, Carol: 0.5 },
  },
  condorcet_winner: 'Alice',
  all_outcomes: {
    'Alice,Bob,Carol': { outcome: 'Alice', sequence: ['Alice', 'Bob', 'Carol'] },
  },
  achievable_outcomes: ['Alice'],
  optimal_agenda: {
    for_target: ['Alice', 'Bob', 'Carol'],
    neutral:    ['Alice', 'Bob', 'Carol'],
    worst_case: ['Carol', 'Bob', 'Alice'],
  },
  manipulation_power: 0.33,
  pedagogical_note: 'Alice is the Condorcet winner.',
};

const CYCLE_DATA = {
  ...MOCK_DATA,
  condorcet_winner: null,
  achievable_outcomes: ['Alice', 'Bob', 'Carol'],
  manipulation_power: 1.0,
  pairwise_matrix: {
    Alice: { Alice: 0.5, Bob: 0.6, Carol: 0.4 },
    Bob:   { Alice: 0.4, Bob: 0.5, Carol: 0.6 },
    Carol: { Alice: 0.6, Bob: 0.4, Carol: 0.5 },
  },
  pedagogical_note: 'Full Condorcet cycle.',
};

describe('AgendaManipulationPanel', () => {
  beforeEach(() => jest.clearAllMocks());

  it('renders controls and simulate button', () => {
    render(<AgendaManipulationPanel />);
    expect(screen.getByTestId('simulate-btn')).toBeInTheDocument();
    expect(screen.getByTestId('voters-input')).toBeInTheDocument();
    expect(screen.getByTestId('seed-input')).toBeInTheDocument();
    expect(screen.getByTestId('target-select')).toBeInTheDocument();
  });

  it('shows prompt alert before simulation', () => {
    render(<AgendaManipulationPanel />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('calls API and renders results on simulate', async () => {
    mockAxios.post.mockResolvedValueOnce({ data: MOCK_DATA });
    render(<AgendaManipulationPanel />);

    await act(async () => {
      fireEvent.click(screen.getByTestId('simulate-btn'));
    });

    await waitFor(() => expect(mockAxios.post).toHaveBeenCalledTimes(1));
    await act(async () => {});

    expect(screen.getByTestId('cw-badge')).toBeInTheDocument();
    expect(screen.getByTestId('power-badge')).toBeInTheDocument();
    expect(screen.getByTestId('agenda-editor')).toBeInTheDocument();
    expect(screen.getByTestId('pairwise-matrix-svg')).toBeInTheDocument();
    expect(screen.getByTestId('achievable-section')).toBeInTheDocument();
    expect(screen.getByTestId('defense-section')).toBeInTheDocument();
  });

  it('shows CW badge with success variant when CW exists', async () => {
    mockAxios.post.mockResolvedValueOnce({ data: MOCK_DATA });
    render(<AgendaManipulationPanel />);

    await act(async () => { fireEvent.click(screen.getByTestId('simulate-btn')); });
    await waitFor(() => expect(mockAxios.post).toHaveBeenCalled());
    await act(async () => {});

    const badge = screen.getByTestId('cw-badge');
    expect(badge).toHaveTextContent('Alice');
  });

  it('shows no-CW badge when cycle detected', async () => {
    mockAxios.post.mockResolvedValueOnce({ data: CYCLE_DATA });
    render(<AgendaManipulationPanel />);

    await act(async () => { fireEvent.click(screen.getByTestId('simulate-btn')); });
    await waitFor(() => expect(mockAxios.post).toHaveBeenCalled());
    await act(async () => {});

    expect(screen.getByTestId('cw-badge')).toHaveTextContent('noCW');
  });

  it('shows full manipulation alert when all outcomes achievable and no CW', async () => {
    mockAxios.post.mockResolvedValueOnce({ data: CYCLE_DATA });
    render(<AgendaManipulationPanel />);

    await act(async () => { fireEvent.click(screen.getByTestId('simulate-btn')); });
    await waitFor(() => expect(mockAxios.post).toHaveBeenCalled());
    await act(async () => {});

    expect(screen.getByTestId('full-manipulation-alert')).toBeInTheDocument();
  });

  it('does NOT show full manipulation alert when CW exists', async () => {
    mockAxios.post.mockResolvedValueOnce({ data: MOCK_DATA });
    render(<AgendaManipulationPanel />);

    await act(async () => { fireEvent.click(screen.getByTestId('simulate-btn')); });
    await waitFor(() => expect(mockAxios.post).toHaveBeenCalled());
    await act(async () => {});

    expect(screen.queryByTestId('full-manipulation-alert')).not.toBeInTheDocument();
  });

  it('renders achievable badges for each alternative', async () => {
    mockAxios.post.mockResolvedValueOnce({ data: MOCK_DATA });
    render(<AgendaManipulationPanel />);

    await act(async () => { fireEvent.click(screen.getByTestId('simulate-btn')); });
    await waitFor(() => expect(mockAxios.post).toHaveBeenCalled());
    await act(async () => {});

    expect(screen.getByTestId('achievable-badge-Alice')).toBeInTheDocument();
    expect(screen.getByTestId('achievable-badge-Bob')).toBeInTheDocument();
    expect(screen.getByTestId('achievable-badge-Carol')).toBeInTheDocument();
  });

  it('applies for_target agenda when "make target win" clicked', async () => {
    mockAxios.post.mockResolvedValueOnce({ data: MOCK_DATA });
    render(<AgendaManipulationPanel />);

    await act(async () => { fireEvent.click(screen.getByTestId('simulate-btn')); });
    await waitFor(() => expect(mockAxios.post).toHaveBeenCalled());
    await act(async () => {});

    fireEvent.click(screen.getByTestId('btn-make-target-win'));
    const editor = screen.getByTestId('agenda-editor');
    expect(editor).toBeInTheDocument();
  });

  it('applies neutral agenda when neutral button clicked', async () => {
    mockAxios.post.mockResolvedValueOnce({ data: MOCK_DATA });
    render(<AgendaManipulationPanel />);

    await act(async () => { fireEvent.click(screen.getByTestId('simulate-btn')); });
    await waitFor(() => expect(mockAxios.post).toHaveBeenCalled());
    await act(async () => {});

    fireEvent.click(screen.getByTestId('btn-neutral'));
    expect(screen.getByTestId('agenda-editor')).toBeInTheDocument();
  });

  it('shows error alert on API failure', async () => {
    mockAxios.post.mockRejectedValueOnce(new Error('Network error'));
    render(<AgendaManipulationPanel />);

    await act(async () => { fireEvent.click(screen.getByTestId('simulate-btn')); });
    await waitFor(() => expect(mockAxios.post).toHaveBeenCalled());
    await act(async () => {});

    expect(screen.getByRole('alert')).toHaveClass('alert-danger');
  });

  it('posts correct payload to API', async () => {
    mockAxios.post.mockResolvedValueOnce({ data: MOCK_DATA });
    render(<AgendaManipulationPanel />);

    await act(async () => { fireEvent.click(screen.getByTestId('simulate-btn')); });
    await waitFor(() => expect(mockAxios.post).toHaveBeenCalled());

    const [url, payload] = mockAxios.post.mock.calls[0];
    expect(url).toContain('/api/theory/agenda-manipulation');
    expect(payload).toHaveProperty('alternatives');
    expect(payload).toHaveProperty('num_voters');
    expect(payload).toHaveProperty('seed');
    expect(payload).toHaveProperty('target_outcome');
    expect(payload).toHaveProperty('constraint_type', 'binary_elimination');
  });
});
