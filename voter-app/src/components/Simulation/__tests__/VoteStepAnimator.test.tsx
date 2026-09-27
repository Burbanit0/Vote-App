import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import VoteStepAnimator from '../VoteStepAnimator';

vi.mock('../../../services/simulationCompareApi', () => ({
  getVoteSteps: vi.fn(),
}));

// Real recharts renders to an SVG jsdom cannot measure, so the pieces that
// carry logic (a bar's colour, the value label, the tooltip text) are invoked
// directly by the mock -- same approach as ManipulabilityChart.test.tsx. Without
// this, PercentBars' `fill` callback and its formatters never run.
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  BarChart: ({ children }: any) => <div data-testid="bar-chart">{children}</div>,
  Bar: ({ children }: any) => <div>{children}</div>,
  CartesianGrid: () => null,
  Cell: ({ fill }: { fill?: string }) => <div data-testid="bar-cell" data-fill={fill} />,
  LabelList: ({ formatter }: { formatter?: (v: number) => string }) =>
    formatter ? <div data-testid="bar-label">{formatter(42)}</div> : null,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: ({ formatter }: { formatter?: (v: number) => [string, string] }) =>
    formatter ? <div data-testid="bar-tooltip">{formatter(42).join('|')}</div> : null,
}));

const { getVoteSteps } = (await import('../../../services/simulationCompareApi')) as unknown as {
  getVoteSteps: jest.Mock;
};

/** VoteStepAnimator's own `C.red` / `C.green`. */
const RED = '#B71C1C';
const GREEN = '#007A33';
// CANDIDATE_COLORS[0] — what the first candidate's bar gets when it is NOT the
// greened winner (the palette's own third colour is also C.green, so counting
// green cells cannot tell the two apart; these tests assert by position).
const FIRST_CANDIDATE = '#005CAB';

const IRV_MOCK = {
  method: 'irv',
  rounds: [
    {
      round: 1,
      scores: { Alice: 0.42, Bob: 0.31, Carol: 0.27 },
      eliminated: null,
      transfers: null,
    },
    {
      round: 2,
      scores: { Alice: 0.55, Bob: 0.45 },
      eliminated: 'Carol',
      transfers: { Alice: 0.08, Bob: 0.19 },
    },
    { round: 3, winner: 'Alice' },
  ],
};

const SCHULZE_MOCK = {
  method: 'schulze',
  duel_matrix: {
    Alice: { Bob: 0.58, Carol: 0.71 },
    Bob: { Alice: 0.42, Carol: 0.53 },
    Carol: { Alice: 0.29, Bob: 0.47 },
  },
  path_matrix: {
    Alice: { Bob: 0.58, Carol: 0.58 },
    Bob: { Alice: 0.47, Carol: 0.53 },
    Carol: { Alice: 0.29, Bob: 0.47 },
  },
  winner: 'Alice',
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.useFakeTimers();
  getVoteSteps.mockResolvedValue(IRV_MOCK);
});

afterEach(() => {
  vi.useRealTimers();
});

describe('VoteStepAnimator', () => {
  it('renders method select and play button', async () => {
    render(<VoteStepAnimator defaultCandidates={['Alice', 'Bob', 'Carol']} />);
    const selects = screen.getAllByRole('combobox');
    expect(selects.length).toBeGreaterThanOrEqual(1); // method + speed selects
    expect(screen.getByText(/Jouer|Play/i)).toBeInTheDocument();
  });

  it('calls getVoteSteps on mount with irv as default method', async () => {
    render(<VoteStepAnimator defaultCandidates={['Alice', 'Bob']} />);
    await waitFor(() => expect(getVoteSteps).toHaveBeenCalledTimes(1));
    expect(getVoteSteps.mock.calls[0][0].method).toBe('irv');
    expect(getVoteSteps.mock.calls[0][0].seed).toBe(42);
  });

  it('passes defaultCandidates to the API', async () => {
    render(<VoteStepAnimator defaultCandidates={['Alice', 'Bob', 'Carol']} />);
    await waitFor(() => expect(getVoteSteps).toHaveBeenCalledTimes(1));
    expect(getVoteSteps.mock.calls[0][0].candidates).toEqual(['Alice', 'Bob', 'Carol']);
  });

  it('calls getVoteSteps again when method changes', async () => {
    render(<VoteStepAnimator defaultCandidates={['Alice', 'Bob']} />);
    await waitFor(() => expect(getVoteSteps).toHaveBeenCalledTimes(1));

    // Change to borda
    const select = screen.getAllByRole('combobox')[0];
    fireEvent.change(select, { target: { value: 'borda' } });

    await waitFor(() => expect(getVoteSteps).toHaveBeenCalledTimes(2));
    expect(getVoteSteps.mock.calls[1][0].method).toBe('borda');
  });

  it('clicking Next advances the step without re-fetching', async () => {
    render(<VoteStepAnimator defaultCandidates={['Alice', 'Bob', 'Carol']} />);
    // Wait for data to load (button enabled)
    await waitFor(() => {
      expect(screen.getByText(/Suivant|Next/i)).not.toBeDisabled();
    });

    fireEvent.click(screen.getByText(/Suivant|Next/i));
    // No extra API call — navigation is client-side
    expect(getVoteSteps).toHaveBeenCalledTimes(1);
  });

  it('clicking Restart resets to step 0', async () => {
    render(<VoteStepAnimator defaultCandidates={['Alice', 'Bob', 'Carol']} />);
    await waitFor(() => expect(getVoteSteps).toHaveBeenCalled());

    const nextBtn = screen.getByText(/Suivant|Next/i);
    const restartBtn = screen.getByText(/Recommencer|Restart/i);

    fireEvent.click(nextBtn); // advance step
    fireEvent.click(restartBtn); // restart

    // No extra API call — still only 1 fetch
    expect(getVoteSteps).toHaveBeenCalledTimes(1);
  });

  it('labels bars as percentages and colours the eliminated candidate red', async () => {
    render(<VoteStepAnimator />);
    await waitFor(() => expect(screen.getByTestId('bar-chart')).toBeInTheDocument());
    // PercentBars' LabelList/Tooltip formatters, applied to a raw 42.
    expect(screen.getByTestId('bar-label')).toHaveTextContent('42%');
    expect(screen.getByTestId('bar-tooltip')).toHaveTextContent('42%|');
    // Round 1 has no elimination: every bar takes its candidate's palette colour.
    const fills = screen.getAllByTestId('bar-cell').map((c) => c.getAttribute('data-fill'));
    expect(fills).toHaveLength(3);
    expect(fills).not.toContain(RED);
  });

  it('colours the eliminated candidate red while they are still on the chart', async () => {
    getVoteSteps.mockResolvedValue({
      method: 'irv',
      rounds: [
        {
          round: 1,
          scores: { Alice: 0.4, Bob: 0.35, Carol: 0.25 },
          eliminated: 'Carol',
          transfers: null,
        },
      ],
    });
    render(<VoteStepAnimator />);
    await waitFor(() => expect(screen.getByTestId('bar-chart')).toBeInTheDocument());
    const fills = screen.getAllByTestId('bar-cell').map((c) => c.getAttribute('data-fill'));
    expect(fills.filter((f) => f === RED)).toHaveLength(1);
  });

  it('announces the winner on the round that has one', async () => {
    render(<VoteStepAnimator />);
    await waitFor(() => expect(screen.getByTestId('bar-chart')).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: /Suivant|Next/i }));
    fireEvent.click(screen.getByRole('button', { name: /Suivant|Next/i }));
    // The IRV round 3 payload is a bare winner, so the chart gives way to the
    // trophy readout.
    expect(screen.getByText(/🏆 Alice/)).toBeInTheDocument();
  });

  it('shows an IRV dead tie as a tie, not a winner', async () => {
    getVoteSteps.mockResolvedValue({
      method: 'irv',
      rounds: [
        { round: 1, scores: { Alice: 0.5, Bob: 0.5 }, eliminated: null, transfers: null },
        { round: 2, winner: null },
      ],
    });
    render(<VoteStepAnimator />);
    await waitFor(() => expect(screen.getByTestId('bar-chart')).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: /Suivant|Next/i }));
    expect(screen.getByTestId('irv-dead-tie')).toHaveTextContent(/Tie \(no winner\)|Égalité/);
    expect(screen.queryByText(/🏆/)).not.toBeInTheDocument();
  });

  it('plurality: greens the winner and announces them', async () => {
    getVoteSteps.mockResolvedValue({
      method: 'plurality',
      first_choices: { Alice: 0.51, Bob: 0.3, Carol: 0.19 },
      winner: 'Alice',
    });
    render(<VoteStepAnimator />);
    await waitFor(() => expect(screen.getByTestId('bar-chart')).toBeInTheDocument());
    const fills = screen.getAllByTestId('bar-cell').map((c) => c.getAttribute('data-fill'));
    expect(fills[0]).toBe(GREEN); // Alice, the winner
    expect(fills[1]).not.toBe(GREEN); // Bob
    expect(screen.getByText(/🏆 Alice/)).toBeInTheDocument();
  });

  it('borda: the winner is only greened on the last step', async () => {
    getVoteSteps.mockResolvedValue({
      method: 'borda',
      steps: [
        { rank: 1, points_awarded: 2, tally: { Alice: 2, Bob: 1, Carol: 0 } },
        { rank: 2, points_awarded: 1, tally: { Alice: 3, Bob: 3, Carol: 1 } },
      ],
      winner: 'Alice',
    });
    render(<VoteStepAnimator />);
    await waitFor(() => expect(screen.getByTestId('bar-chart')).toBeInTheDocument());
    expect(screen.queryByText(/🏆 Alice/)).not.toBeInTheDocument();
    expect(screen.getAllByTestId('bar-cell')[0]).toHaveAttribute('data-fill', FIRST_CANDIDATE);
    fireEvent.click(screen.getByRole('button', { name: /Suivant|Next/i }));
    expect(screen.getByText(/🏆 Alice/)).toBeInTheDocument();
    expect(screen.getAllByTestId('bar-cell')[0]).toHaveAttribute('data-fill', GREEN);
  });

  it('approval: bars split green/red on the threshold', async () => {
    getVoteSteps.mockResolvedValue({
      method: 'approval',
      approval_scores: { Alice: 0.62, Bob: 0.55, Carol: 0.3 },
      threshold_used: 0.5,
      winner: 'Alice',
    });
    render(<VoteStepAnimator />);
    await waitFor(() => expect(screen.getByTestId('bar-chart')).toBeInTheDocument());
    const fills = screen.getAllByTestId('bar-cell').map((c) => c.getAttribute('data-fill'));
    // Alice and Bob clear 50%, Carol does not -- approval colours every bar
    // green or red, so counting is unambiguous here.
    expect(fills).toEqual([GREEN, GREEN, RED]);
    expect(screen.getByText(/🏆 Alice/)).toBeInTheDocument();
  });

  it('renders Schulze heatmap headers when method is schulze', async () => {
    getVoteSteps.mockResolvedValue(SCHULZE_MOCK);
    render(<VoteStepAnimator defaultCandidates={['Alice', 'Bob', 'Carol']} />);

    const select = screen.getAllByRole('combobox')[0];
    fireEvent.change(select, { target: { value: 'schulze' } });

    await waitFor(() => {
      expect(getVoteSteps).toHaveBeenCalledWith(expect.objectContaining({ method: 'schulze' }));
    });
  });

  it('Next button is disabled when on last step', async () => {
    // IRV has 3 rounds, so last step index is 2
    render(<VoteStepAnimator defaultCandidates={['Alice', 'Bob', 'Carol']} />);
    await waitFor(() => expect(getVoteSteps).toHaveBeenCalled());

    const nextBtn = screen.getByText(/Suivant|Next/i);
    fireEvent.click(nextBtn); // step 1
    fireEvent.click(nextBtn); // step 2 (last)

    expect(nextBtn).toBeDisabled();
  });
});
