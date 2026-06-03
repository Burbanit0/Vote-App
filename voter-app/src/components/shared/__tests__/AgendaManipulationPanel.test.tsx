import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import AgendaManipulationPanel from '../AgendaManipulationPanel';
import { makeTestQueryClient } from '../../../test/queryWrapper';

vi.mock('../../../api/client', () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn(), PATCH: vi.fn() },
  getAccessToken: vi.fn(() => null),
}));
const { apiClient } = (await import('../../../api/client')) as unknown as { apiClient: { POST: jest.Mock } };

vi.mock('react-i18next', () => ({
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

const ok = (d: unknown) => ({ data: d, error: undefined });

function renderPanel() {
  return render(
    <QueryClientProvider client={makeTestQueryClient()}>
      <AgendaManipulationPanel />
    </QueryClientProvider>
  );
}

describe('AgendaManipulationPanel', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders controls and simulate button', () => {
    renderPanel();
    expect(screen.getByTestId('simulate-btn')).toBeInTheDocument();
    expect(screen.getByTestId('voters-input')).toBeInTheDocument();
    expect(screen.getByTestId('seed-input')).toBeInTheDocument();
    expect(screen.getByTestId('target-select')).toBeInTheDocument();
  });

  it('shows prompt alert before simulation', () => {
    renderPanel();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('calls API and renders results on simulate', async () => {
    apiClient.POST.mockResolvedValueOnce(ok(MOCK_DATA));
    renderPanel();
    await act(async () => { fireEvent.click(screen.getByTestId('simulate-btn')); });
    await waitFor(() => expect(screen.getByTestId('cw-badge')).toBeInTheDocument());
    expect(screen.getByTestId('power-badge')).toBeInTheDocument();
    expect(screen.getByTestId('agenda-editor')).toBeInTheDocument();
    expect(screen.getByTestId('pairwise-matrix-svg')).toBeInTheDocument();
    expect(screen.getByTestId('achievable-section')).toBeInTheDocument();
    expect(screen.getByTestId('defense-section')).toBeInTheDocument();
  });

  it('shows CW badge with success variant when CW exists', async () => {
    apiClient.POST.mockResolvedValueOnce(ok(MOCK_DATA));
    renderPanel();
    await act(async () => { fireEvent.click(screen.getByTestId('simulate-btn')); });
    await waitFor(() => expect(screen.getByTestId('cw-badge')).toHaveTextContent('Alice'));
  });

  it('shows no-CW badge when cycle detected', async () => {
    apiClient.POST.mockResolvedValueOnce(ok(CYCLE_DATA));
    renderPanel();
    await act(async () => { fireEvent.click(screen.getByTestId('simulate-btn')); });
    await waitFor(() => expect(screen.getByTestId('cw-badge')).toHaveTextContent('noCW'));
  });

  it('shows full manipulation alert when all outcomes achievable and no CW', async () => {
    apiClient.POST.mockResolvedValueOnce(ok(CYCLE_DATA));
    renderPanel();
    await act(async () => { fireEvent.click(screen.getByTestId('simulate-btn')); });
    await waitFor(() => expect(screen.getByTestId('full-manipulation-alert')).toBeInTheDocument());
  });

  it('does NOT show full manipulation alert when CW exists', async () => {
    apiClient.POST.mockResolvedValueOnce(ok(MOCK_DATA));
    renderPanel();
    await act(async () => { fireEvent.click(screen.getByTestId('simulate-btn')); });
    await waitFor(() => expect(screen.getByTestId('cw-badge')).toBeInTheDocument());
    expect(screen.queryByTestId('full-manipulation-alert')).not.toBeInTheDocument();
  });

  it('renders achievable badges for each alternative', async () => {
    apiClient.POST.mockResolvedValueOnce(ok(MOCK_DATA));
    renderPanel();
    await act(async () => { fireEvent.click(screen.getByTestId('simulate-btn')); });
    await waitFor(() => expect(screen.getByTestId('achievable-badge-Alice')).toBeInTheDocument());
    expect(screen.getByTestId('achievable-badge-Bob')).toBeInTheDocument();
    expect(screen.getByTestId('achievable-badge-Carol')).toBeInTheDocument();
  });

  it('applies for_target agenda when "make target win" clicked', async () => {
    apiClient.POST.mockResolvedValueOnce(ok(MOCK_DATA));
    renderPanel();
    await act(async () => { fireEvent.click(screen.getByTestId('simulate-btn')); });
    await waitFor(() => expect(screen.getByTestId('agenda-editor')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('btn-make-target-win'));
    expect(screen.getByTestId('agenda-editor')).toBeInTheDocument();
  });

  it('applies neutral agenda when neutral button clicked', async () => {
    apiClient.POST.mockResolvedValueOnce(ok(MOCK_DATA));
    renderPanel();
    await act(async () => { fireEvent.click(screen.getByTestId('simulate-btn')); });
    await waitFor(() => expect(screen.getByTestId('agenda-editor')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('btn-neutral'));
    expect(screen.getByTestId('agenda-editor')).toBeInTheDocument();
  });

  it('shows error alert on API failure', async () => {
    apiClient.POST.mockRejectedValueOnce(new Error('Network error'));
    renderPanel();
    await act(async () => { fireEvent.click(screen.getByTestId('simulate-btn')); });
    await waitFor(() => expect(screen.getByRole('alert')).toHaveClass('bg-red-100'));
  });

  it('posts correct payload to API', async () => {
    apiClient.POST.mockResolvedValueOnce(ok(MOCK_DATA));
    renderPanel();
    await act(async () => { fireEvent.click(screen.getByTestId('simulate-btn')); });
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalled());
    const [url, init] = apiClient.POST.mock.calls[0];
    expect(url).toBe('/api/v2/theory/agenda-manipulation');
    const payload = (init as { body: Record<string, unknown> }).body;
    expect(payload).toHaveProperty('alternatives');
    expect(payload).toHaveProperty('num_voters');
    expect(payload).toHaveProperty('seed');
    expect(payload).toHaveProperty('target_outcome');
    expect(payload).toHaveProperty('constraint_type', 'binary_elimination');
  });
});
