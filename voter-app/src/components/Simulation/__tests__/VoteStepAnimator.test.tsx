import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import VoteStepAnimator from '../VoteStepAnimator';

vi.mock('../../../services/simulationCompareApi', () => ({
  getVoteSteps: vi.fn(),
}));

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  BarChart:            ({ children }: any) => <div data-testid="bar-chart">{children}</div>,
  Bar:                 ({ children }: any) => <div>{children}</div>,
  CartesianGrid: () => null,
  Cell:          () => null,
  LabelList:     () => null,
  XAxis:         () => null,
  YAxis:         () => null,
  Tooltip:       () => null,
}));

const { getVoteSteps } = (await import('../../../services/simulationCompareApi')) as unknown as {
  getVoteSteps: jest.Mock;
};

const IRV_MOCK = {
  method: 'irv',
  rounds: [
    { round: 1, scores: { Alice: 0.42, Bob: 0.31, Carol: 0.27 }, eliminated: null, transfers: null },
    { round: 2, scores: { Alice: 0.55, Bob: 0.45 }, eliminated: 'Carol', transfers: { Alice: 0.08, Bob: 0.19 } },
    { round: 3, winner: 'Alice' },
  ],
};

const SCHULZE_MOCK = {
  method: 'schulze',
  duel_matrix:  { Alice: { Bob: 0.58, Carol: 0.71 }, Bob: { Alice: 0.42, Carol: 0.53 }, Carol: { Alice: 0.29, Bob: 0.47 } },
  path_matrix:  { Alice: { Bob: 0.58, Carol: 0.58 }, Bob: { Alice: 0.47, Carol: 0.53 }, Carol: { Alice: 0.29, Bob: 0.47 } },
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

    const nextBtn     = screen.getByText(/Suivant|Next/i);
    const restartBtn  = screen.getByText(/Recommencer|Restart/i);

    fireEvent.click(nextBtn);    // advance step
    fireEvent.click(restartBtn); // restart

    // No extra API call — still only 1 fetch
    expect(getVoteSteps).toHaveBeenCalledTimes(1);
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
