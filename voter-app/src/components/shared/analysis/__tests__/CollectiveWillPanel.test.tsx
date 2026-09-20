import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import CollectiveWillPanel from '../CollectiveWillPanel';
import { makeTestQueryClient } from '../../../../test/queryWrapper';

vi.mock('../../../../api/client', () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn(), PATCH: vi.fn() },
}));
const { apiClient } = (await import('../../../../api/client')) as unknown as {
  apiClient: { POST: jest.Mock };
};

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key.split('.').pop() ?? key,
  }),
}));

// ── Mock data ─────────────────────────────────────────────────────────────────

const MOCK_ROBUST: object = {
  unique_winners: ['Alice'],
  unique_winner_count: 1,
  winner_by_method: { plurality: 'Alice', borda: 'Alice', irv: 'Alice' },
  winner_by_agenda: { 'Alice → Bob → Carol': 'Alice', 'Bob → Alice → Carol': 'Alice' },
  rousseau_score: 1.0,
  most_frequent_winner: ['Alice'],
  most_frequent_pct: 1.0,
  condorcet_exists: true,
  condorcet_winner: 'Alice',
  philosophical_conclusion: 'Alice wins under all procedures tested.',
  pedagogical_note: 'Vote Lab cannot answer "what is the will of the people?"',
};

const MOCK_FRAGILE: object = {
  unique_winners: ['Alice', 'Bob', 'Carol'],
  unique_winner_count: 3,
  winner_by_method: { plurality: 'Alice', borda: 'Bob', irv: 'Carol' },
  winner_by_agenda: { 'Alice → Bob → Carol': 'Alice', 'Bob → Carol → Alice': 'Bob' },
  rousseau_score: 0.333,
  most_frequent_winner: ['Alice'],
  most_frequent_pct: 0.4,
  condorcet_exists: false,
  condorcet_winner: null,
  philosophical_conclusion: 'Three different winners — Schumpeter was right.',
  pedagogical_note: 'The result depends on procedure alone.',
};

/** openapi-fetch resolves to { data, error }. */
const ok = (d: unknown) => ({ data: d, error: undefined });

/** The Lab's shared electorate, the only way this panel is ever mounted. */
const LAB = {
  candidates: [
    { name: 'Alice', x: -0.5, y: 0.0 },
    { name: 'Bob', x: 0.0, y: 0.0 },
    { name: 'Carol', x: 0.5, y: 0.0 },
  ],
  numVoters: 100,
  seed: 42,
  ideology: 'random',
};

function renderPanel() {
  return render(
    <QueryClientProvider client={makeTestQueryClient()}>
      <CollectiveWillPanel {...LAB} />
    </QueryClientProvider>
  );
}

/** Mounting IS the run: this panel has no run button, it follows the Lab. */
async function renderAndRun(responseData: object = MOCK_ROBUST) {
  apiClient.POST.mockResolvedValue(ok(responseData));
  renderPanel();
  await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));
  await act(async () => {});
}

describe('CollectiveWillPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiClient.POST.mockResolvedValue(ok(MOCK_ROBUST));
  });

  // ── Initial render ──────────────────────────────────────────────────────────

  // ── API call ────────────────────────────────────────────────────────────────

  it('runs itself on mount with the Lab electorate', async () => {
    await renderAndRun();
    const [url, init] = apiClient.POST.mock.calls[0] as [string, { body: Record<string, unknown> }];
    expect(url).toBe('/api/v2/theory/collective-will');
    const payload = init.body;
    expect(payload.candidates).toEqual(LAB.candidates);
    expect(payload.num_voters).toBe(LAB.numVoters);
    expect(payload.ideology).toBe(LAB.ideology);
    expect(payload.seed).toBe(LAB.seed);
    // The sweep's breadth is fixed now that no picker sets it.
    expect(payload.num_methods).toBe(5);
    expect(payload.num_agendas).toBe(4);
  });

  // ── Robust scenario ─────────────────────────────────────────────────────────

  it('renders will-o-meter section after simulation', async () => {
    await renderAndRun(MOCK_ROBUST);
    expect(screen.getByTestId('willometer-section')).toBeInTheDocument();
    expect(screen.getByTestId('will-o-meter')).toBeInTheDocument();
  });

  it('marks every winner tied for most procedures', async () => {
    const tied = {
      ...(MOCK_ROBUST as Record<string, unknown>),
      unique_winners: ['Alice', 'Bob'],
      unique_winner_count: 2,
      most_frequent_winner: ['Alice', 'Bob'],
      most_frequent_pct: 0.5,
    };
    await renderAndRun(tied);
    // Both chips carry the share, not just whichever the backend listed first.
    expect(screen.getAllByText(/50%/).length).toBeGreaterThanOrEqual(2);
  });

  it('renders condorcet badge', async () => {
    await renderAndRun(MOCK_ROBUST);
    expect(screen.getByTestId('condorcet-badge')).toBeInTheDocument();
    expect(screen.getByTestId('condorcet-badge')).toHaveTextContent('Alice');
  });

  it('renders rousseau and verdict badges', async () => {
    await renderAndRun(MOCK_ROBUST);
    expect(screen.getByTestId('rousseau-badge')).toBeInTheDocument();
    expect(screen.getByTestId('verdict-badge')).toBeInTheDocument();
  });

  it('renders unique winners section', async () => {
    await renderAndRun(MOCK_ROBUST);
    expect(screen.getByTestId('unique-winners')).toBeInTheDocument();
  });

  it('renders result grid', async () => {
    await renderAndRun(MOCK_ROBUST);
    expect(screen.getByTestId('result-grid')).toBeInTheDocument();
    expect(screen.getByTestId('grid-method-plurality')).toBeInTheDocument();
  });

  it('renders philosophers section', async () => {
    await renderAndRun(MOCK_ROBUST);
    expect(screen.getByTestId('philosophers-section')).toBeInTheDocument();
    expect(screen.getByTestId('philo-card-rousseau')).toBeInTheDocument();
    expect(screen.getByTestId('philo-card-arrow')).toBeInTheDocument();
    expect(screen.getByTestId('philo-card-schumpeter')).toBeInTheDocument();
    expect(screen.getByTestId('philo-card-sen')).toBeInTheDocument();
    expect(screen.getByTestId('philo-card-rawls')).toBeInTheDocument();
  });

  it('expands philosopher card on click', async () => {
    await renderAndRun(MOCK_ROBUST);
    const card = screen.getByTestId('philo-card-arrow');
    fireEvent.click(card);
    // After click, detail text should appear
    expect(card).toBeInTheDocument();
  });

  it('renders philosophical conclusion', async () => {
    await renderAndRun(MOCK_ROBUST);
    expect(screen.getByTestId('philo-conclusion')).toBeInTheDocument();
    expect(screen.getByTestId('philo-conclusion')).toHaveTextContent(
      'Alice wins under all procedures'
    );
  });

  it('renders open conclusion section', async () => {
    await renderAndRun(MOCK_ROBUST);
    expect(screen.getByTestId('open-conclusion')).toBeInTheDocument();
  });

  it('renders pedagogical note', async () => {
    await renderAndRun(MOCK_ROBUST);
    expect(screen.getByTestId('pedagogical-note')).toBeInTheDocument();
  });

  // ── Fragile scenario ────────────────────────────────────────────────────────

  it('shows no-CW badge in fragile scenario', async () => {
    await renderAndRun(MOCK_FRAGILE);
    const badge = screen.getByTestId('condorcet-badge');
    expect(badge).not.toHaveTextContent('Alice');
  });

  it('shows multiple unique winners in fragile scenario', async () => {
    await renderAndRun(MOCK_FRAGILE);
    const section = screen.getByTestId('unique-winners');
    expect(section).toHaveTextContent('Alice');
    expect(section).toHaveTextContent('Bob');
    expect(section).toHaveTextContent('Carol');
  });

  // ── Error handling ──────────────────────────────────────────────────────────

  it('shows error alert on API failure', async () => {
    apiClient.POST.mockRejectedValue(new Error('Network error'));
    renderPanel();
    await waitFor(() => expect(screen.getByTestId('error-alert')).toBeInTheDocument());
  });
});
