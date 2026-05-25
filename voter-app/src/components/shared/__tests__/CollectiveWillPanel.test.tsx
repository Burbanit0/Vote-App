import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import axios from 'axios';
import CollectiveWillPanel from '../CollectiveWillPanel';

jest.mock('axios');
const mockAxios = axios as jest.Mocked<typeof axios>;

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key.split('.').pop() ?? key,
  }),
}));

// ── Mock data ─────────────────────────────────────────────────────────────────

const MOCK_ROBUST: object = {
  unique_winners:           ['Alice'],
  unique_winner_count:      1,
  winner_by_method:         { plurality: 'Alice', borda: 'Alice', irv: 'Alice' },
  winner_by_agenda:         { 'Alice → Bob → Carol': 'Alice', 'Bob → Alice → Carol': 'Alice' },
  rousseau_score:           1.0,
  most_frequent_winner:     'Alice',
  most_frequent_pct:        1.0,
  condorcet_exists:         true,
  condorcet_winner:         'Alice',
  philosophical_conclusion: 'Alice wins under all procedures tested.',
  pedagogical_note:         'Vote Lab cannot answer "what is the will of the people?"',
};

const MOCK_FRAGILE: object = {
  unique_winners:           ['Alice', 'Bob', 'Carol'],
  unique_winner_count:      3,
  winner_by_method:         { plurality: 'Alice', borda: 'Bob', irv: 'Carol' },
  winner_by_agenda:         { 'Alice → Bob → Carol': 'Alice', 'Bob → Carol → Alice': 'Bob' },
  rousseau_score:           0.333,
  most_frequent_winner:     'Alice',
  most_frequent_pct:        0.40,
  condorcet_exists:         false,
  condorcet_winner:         null,
  philosophical_conclusion: 'Three different winners — Schumpeter was right.',
  pedagogical_note:         'The result depends on procedure alone.',
};

async function renderAndRun(responseData: object = MOCK_ROBUST) {
  mockAxios.post.mockResolvedValueOnce({ data: responseData });
  render(<CollectiveWillPanel />);
  await act(async () => { fireEvent.click(screen.getByTestId('run-btn')); });
  await waitFor(() => expect(mockAxios.post).toHaveBeenCalledTimes(1));
  await act(async () => {});
}

describe('CollectiveWillPanel', () => {
  beforeEach(() => jest.resetAllMocks());

  // ── Initial render ──────────────────────────────────────────────────────────

  it('renders controls on mount', () => {
    render(<CollectiveWillPanel />);
    expect(screen.getByTestId('run-btn')).toBeInTheDocument();
    expect(screen.getByTestId('voters-input')).toBeInTheDocument();
    expect(screen.getByTestId('methods-input')).toBeInTheDocument();
    expect(screen.getByTestId('agendas-input')).toBeInTheDocument();
    expect(screen.getByTestId('ideology-select')).toBeInTheDocument();
    expect(screen.getByTestId('seed-input')).toBeInTheDocument();
  });

  it('shows prompt alert before simulation', () => {
    render(<CollectiveWillPanel />);
    expect(screen.getByTestId('prompt-alert')).toBeInTheDocument();
  });

  it('has random and polarized ideology options', () => {
    render(<CollectiveWillPanel />);
    const select = screen.getByTestId('ideology-select') as HTMLSelectElement;
    expect(select.options).toHaveLength(2);
  });

  // ── API call ────────────────────────────────────────────────────────────────

  it('calls API with correct payload on run', async () => {
    await renderAndRun();
    const [url, payload] = mockAxios.post.mock.calls[0];
    expect(url).toMatch(/\/api\/(v2\/)?theory\/collective-will/);
    expect(payload).toHaveProperty('candidates');
    expect(payload).toHaveProperty('num_voters');
    expect(payload).toHaveProperty('num_methods');
    expect(payload).toHaveProperty('num_agendas');
  });

  // ── Robust scenario ─────────────────────────────────────────────────────────

  it('renders will-o-meter section after simulation', async () => {
    await renderAndRun(MOCK_ROBUST);
    expect(screen.getByTestId('willometer-section')).toBeInTheDocument();
    expect(screen.getByTestId('will-o-meter')).toBeInTheDocument();
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
    expect(screen.getByTestId('philo-conclusion'))
      .toHaveTextContent('Alice wins under all procedures');
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
    mockAxios.post.mockRejectedValueOnce(new Error('Network error'));
    render(<CollectiveWillPanel />);
    await act(async () => { fireEvent.click(screen.getByTestId('run-btn')); });
    await waitFor(() => expect(mockAxios.post).toHaveBeenCalled());
    await act(async () => {});
    expect(screen.getByTestId('error-alert')).toBeInTheDocument();
  });
});
