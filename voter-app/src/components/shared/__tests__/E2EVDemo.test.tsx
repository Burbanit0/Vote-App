import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import E2EVDemo from '../E2EVDemo';
import { makeTestQueryClient } from '../../../test/queryWrapper';

jest.mock('../../../api/client', () => ({
  apiClient: { GET: jest.fn(), POST: jest.fn(), PUT: jest.fn(), DELETE: jest.fn(), PATCH: jest.fn() },
  getAccessToken: jest.fn(() => null),
}));
const { apiClient } = jest.requireMock('../../../api/client') as { apiClient: { POST: jest.Mock } };

// ── Fixture ───────────────────────────────────────────────────────────────────

function makeData(userVote = 'Alice') {
  const VOTERS = 12;
  const voters = Array.from({ length: VOTERS }, (_, i) => ({
    id:                i + 1,
    encrypted_ballot:  `[AB${i}CD${i}EF…]`,
    verification_code: `A${i}B-C${i}D-E${i}F`,
    vote_HIDDEN:       i === 0 ? userVote : ['Alice', 'Bob', 'Carol'][i % 3],
  }));

  // Shuffled board (voter 1's code at index 7)
  const board = [...voters].map((v) => ({
    encrypted_ballot:  v.encrypted_ballot,
    verification_code: v.verification_code,
  }));
  // Put voter 1 code somewhere in the middle
  const myEntry = board.splice(0, 1)[0];
  board.splice(7, 0, myEntry);

  return {
    data: {
      voters,
      public_bulletin_board: board,
      aggregate_result: { Alice: 6, Bob: 4, Carol: 2 },
      winner: 'Alice',
      audit_proof: 'Tous les 12 bulletins sont dans l\'urne.',
      num_voters: VOTERS,
      candidates: ['Alice', 'Bob', 'Carol'],
      encrypted_ballots: voters.map((v) => ({ voter_id: v.id, encrypted: v.encrypted_ballot, code: v.verification_code })),
      verification_demonstration: { sample_voter_id: 1, sample_code: voters[0].verification_code, board_excerpt: [] },
      privacy_guarantee: 'Test.',
    },
    error: undefined,
  };
}

function renderDemo() {
  return render(
    <MemoryRouter>
      <QueryClientProvider client={makeTestQueryClient()}>
        <E2EVDemo candidates={['Alice', 'Bob', 'Carol']} seed={42} />
      </QueryClientProvider>
    </MemoryRouter>
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  jest.useFakeTimers();
});

afterEach(() => { jest.useRealTimers(); });

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('E2EVDemo', () => {
  it('shows candidate selection buttons', () => {
    renderDemo();
    expect(screen.getByTestId('candidate-btn-Alice')).toBeInTheDocument();
    expect(screen.getByTestId('candidate-btn-Bob')).toBeInTheDocument();
    expect(screen.getByTestId('candidate-btn-Carol')).toBeInTheDocument();
  });

  it('vote button disabled until candidate selected', () => {
    renderDemo();
    expect(screen.getByTestId('vote-btn')).toBeDisabled();
  });

  it('vote button enabled after selecting a candidate', () => {
    renderDemo();
    fireEvent.click(screen.getByTestId('candidate-btn-Alice'));
    expect(screen.getByTestId('vote-btn')).not.toBeDisabled();
  });

  it('calls API with correct user_vote when voting', async () => {
    apiClient.POST.mockResolvedValue(makeData('Bob'));
    renderDemo();
    fireEvent.click(screen.getByTestId('candidate-btn-Bob'));
    fireEvent.click(screen.getByTestId('vote-btn'));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));
    expect(apiClient.POST).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/(v2\/)?tech\/e2e-demo/),
      expect.objectContaining({ body: expect.objectContaining({ user_vote: 'Bob' }) }),
    );
    jest.runAllTimers();
  });

  it('shows step 1 content after voting (encrypted ballot + code)', async () => {
    apiClient.POST.mockResolvedValue(makeData('Alice'));
    renderDemo();
    fireEvent.click(screen.getByTestId('candidate-btn-Alice'));
    fireEvent.click(screen.getByTestId('vote-btn'));
    await waitFor(() => expect(screen.getByTestId('step1-content')).toBeInTheDocument());
    expect(screen.getByTestId('my-verification-code')).toBeInTheDocument();
    jest.runAllTimers();
  });

  it('advances to step 2 (bulletin board)', async () => {
    apiClient.POST.mockResolvedValue(makeData('Alice'));
    renderDemo();
    fireEvent.click(screen.getByTestId('candidate-btn-Alice'));
    fireEvent.click(screen.getByTestId('vote-btn'));
    await waitFor(() => screen.getByTestId('next-step-btn'));
    fireEvent.click(screen.getByTestId('next-step-btn'));
    expect(screen.getByTestId('step2-content')).toBeInTheDocument();
    expect(screen.getByTestId('bulletin-board')).toBeInTheDocument();
    jest.runAllTimers();
  });

  it('shows "code found" alert when user clicks their code on the board', async () => {
    apiClient.POST.mockResolvedValue(makeData('Alice'));
    renderDemo();
    fireEvent.click(screen.getByTestId('candidate-btn-Alice'));
    fireEvent.click(screen.getByTestId('vote-btn'));
    await waitFor(() => screen.getByTestId('next-step-btn'));
    fireEvent.click(screen.getByTestId('next-step-btn'));
    // Click the highlighted entry (voter 1's code)
    const board = screen.getByTestId('bulletin-board');
    const highlighted = board.querySelector('.border-warning');
    if (highlighted) fireEvent.click(highlighted);
    await waitFor(() => expect(screen.queryByTestId('code-found-alert')).not.toBeNull());
    jest.runAllTimers();
  });

  it('advances to step 3 (aggregate)', async () => {
    apiClient.POST.mockResolvedValue(makeData('Alice'));
    renderDemo();
    fireEvent.click(screen.getByTestId('candidate-btn-Alice'));
    fireEvent.click(screen.getByTestId('vote-btn'));
    await waitFor(() => screen.getByTestId('next-step-btn'));
    fireEvent.click(screen.getByTestId('next-step-btn'));
    await waitFor(() => screen.getByTestId('to-step3-btn'));
    fireEvent.click(screen.getByTestId('to-step3-btn'));
    expect(screen.getByTestId('step3-content')).toBeInTheDocument();
    expect(screen.getByTestId('aggregate-display')).toBeInTheDocument();
    jest.runAllTimers();
  });

  it('advances to step 4 (reveal)', async () => {
    apiClient.POST.mockResolvedValue(makeData('Alice'));
    renderDemo();
    fireEvent.click(screen.getByTestId('candidate-btn-Alice'));
    fireEvent.click(screen.getByTestId('vote-btn'));
    await waitFor(() => screen.getByTestId('next-step-btn'));
    fireEvent.click(screen.getByTestId('next-step-btn'));
    await waitFor(() => screen.getByTestId('to-step3-btn'));
    fireEvent.click(screen.getByTestId('to-step3-btn'));
    await waitFor(() => screen.getByTestId('to-step4-btn'));
    fireEvent.click(screen.getByTestId('to-step4-btn'));
    expect(screen.getByTestId('step4-content')).toBeInTheDocument();
    expect(screen.getByTestId('reveal-btn')).toBeInTheDocument();
    jest.runAllTimers();
  });

  it('reveals vote when reveal button clicked', async () => {
    apiClient.POST.mockResolvedValue(makeData('Alice'));
    renderDemo();
    fireEvent.click(screen.getByTestId('candidate-btn-Alice'));
    fireEvent.click(screen.getByTestId('vote-btn'));
    await waitFor(() => screen.getByTestId('next-step-btn'));
    for (const id of ['next-step-btn', 'to-step3-btn', 'to-step4-btn']) {
      await waitFor(() => screen.getByTestId(id));
      fireEvent.click(screen.getByTestId(id));
    }
    await waitFor(() => screen.getByTestId('reveal-btn'));
    fireEvent.click(screen.getByTestId('reveal-btn'));
    expect(screen.getByTestId('revealed-result')).toBeInTheDocument();
    jest.runAllTimers();
  });

  it('shows error on API failure', async () => {
    apiClient.POST.mockRejectedValue(new Error('Network error'));
    renderDemo();
    fireEvent.click(screen.getByTestId('candidate-btn-Alice'));
    fireEvent.click(screen.getByTestId('vote-btn'));
    await waitFor(() => expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument());
  });
});
