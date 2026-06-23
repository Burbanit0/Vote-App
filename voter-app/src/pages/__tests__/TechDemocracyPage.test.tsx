import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import TechDemocracyPage from '../TechDemocracyPage';
import { makeTestQueryClient } from '../../test/queryWrapper';

vi.mock('../../api/client', () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn(), PATCH: vi.fn() },
  getAccessToken: vi.fn(() => null),
}));
const { apiClient } = (await import('../../api/client')) as unknown as {
  apiClient: { POST: jest.Mock };
};

// ── Fixtures ──────────────────────────────────────────────────────────────────

// Matches the E2EFullData shape consumed by E2EVDemo ($api.useMutation →
// apiClient.POST returns { data, error }).
function makeE2EData() {
  return {
    data: {
      voters: Array.from({ length: 12 }, (_, i) => ({
        id: i + 1,
        encrypted_ballot: `[AB${i}CD${i}EF…]`,
        verification_code: `A${i}B-C${i}D-E${i}F`,
        vote_HIDDEN: 'Alice',
      })),
      public_bulletin_board: Array.from({ length: 12 }, (_, i) => ({
        encrypted_ballot: `[AB${i}CD${i}EF…]`,
        verification_code: `A${i}B-C${i}D-E${i}F`,
      })),
      aggregate_result: { Alice: 5, Bob: 4, Carol: 3 },
      winner: 'Alice',
      audit_proof: 'Σ encrypted ballots = encrypted total (homomorphic).',
    },
    error: undefined,
  };
}

function makePolisData(numClusters = 2) {
  const statements = ['Stmt A', 'Stmt B', 'Stmt C'];
  const clusters = Array.from({ length: numClusters }, (_, i) => ({
    id: i,
    size: 50,
    votes: Object.fromEntries(statements.map((s) => [s, i === 0 ? 0.85 : 0.25])),
  }));
  return {
    data: {
      clusters,
      consensus_statements: [{ statement: 'Stmt A', approval_rate: 0.85 }],
      polarizing_statements: [{ statement: 'Stmt B', cluster_delta: 0.6 }],
      participant_positions: Array.from({ length: 10 }, (_, i) => ({
        id: i,
        x_pca: (i - 5) * 0.2,
        y_pca: (i - 5) * 0.1,
        cluster_id: i % numClusters,
      })),
      num_clusters: numClusters,
      num_participants: 10,
    },
    error: undefined,
  };
}

function renderPage() {
  return render(
    <MemoryRouter>
      <QueryClientProvider client={makeTestQueryClient()}>
        <TechDemocracyPage />
      </QueryClientProvider>
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('TechDemocracyPage', () => {
  it('renders the page with its main sections', () => {
    renderPage();
    // Updated to match the actual rendered section IDs (the old "e2e-section"
    // was renamed to "e2ev-interactive-section" at some point).
    expect(screen.getByTestId('why-hard-section')).toBeInTheDocument();
    expect(screen.getByTestId('three-approaches-section')).toBeInTheDocument();
    expect(screen.getByTestId('e2ev-interactive-section')).toBeInTheDocument();
    expect(screen.getByTestId('blockchain-table-section')).toBeInTheDocument();
    expect(screen.getByTestId('polis-section')).toBeInTheDocument();
  });

  // The E2E-V demo is the interactive E2EVDemo component (components/shared/
  // E2EVDemo.tsx): pick a candidate → vote → step through bulletin board →
  // homomorphic count. Helper drives it to its first step.
  async function voteAndAdvance() {
    apiClient.POST.mockResolvedValue(makeE2EData());
    renderPage();
    fireEvent.click(screen.getByTestId('candidate-btn-Alice'));
    fireEvent.click(screen.getByTestId('vote-btn'));
    await waitFor(() => expect(screen.getByTestId('step1-content')).toBeInTheDocument());
  }

  it('shows the E2E-V vote controls (candidate buttons + vote)', () => {
    renderPage();
    expect(screen.getByTestId('candidate-btn-Alice')).toBeInTheDocument();
    expect(screen.getByTestId('vote-btn')).toBeInTheDocument();
  });

  it('shows Pol.is run button', () => {
    renderPage();
    expect(screen.getByTestId('run-polis-btn')).toBeInTheDocument();
  });

  it('shows ideology selector for Pol.is', () => {
    renderPage();
    // The page mounts its own Pol.is controls plus the PolisPanel, both of which
    // expose an ideology-select — assert at least one is present.
    expect(screen.getAllByTestId('ideology-select').length).toBeGreaterThanOrEqual(1);
  });

  it('shows num-clusters input', () => {
    renderPage();
    expect(screen.getByTestId('num-clusters-input')).toBeInTheDocument();
  });

  // ── E2E-V demo ────────────────────────────────────────────────────────────

  it('calls the e2e-demo API when a vote is cast', async () => {
    apiClient.POST.mockResolvedValue(makeE2EData());
    renderPage();
    fireEvent.click(screen.getByTestId('candidate-btn-Alice'));
    fireEvent.click(screen.getByTestId('vote-btn'));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalled());
    expect(apiClient.POST).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/(v2\/)?tech\/e2e-demo/),
      expect.any(Object)
    );
  });

  it('shows the encrypted ballot + verification code after voting', async () => {
    await voteAndAdvance();
    expect(screen.getByTestId('my-verification-code')).toBeInTheDocument();
    expect(screen.getByTestId('my-verification-code')).toHaveTextContent('A0B-C0D-E0F');
  });

  it('shows the next-step button after voting', async () => {
    await voteAndAdvance();
    expect(screen.getByTestId('next-step-btn')).toBeInTheDocument();
  });

  it('shows the public bulletin board at step 2', async () => {
    await voteAndAdvance();
    fireEvent.click(screen.getByTestId('next-step-btn')); // → step 2
    expect(screen.getByTestId('bulletin-board')).toBeInTheDocument();
  });

  it('shows the homomorphic aggregate result at step 3', async () => {
    await voteAndAdvance();
    fireEvent.click(screen.getByTestId('next-step-btn')); // → step 2
    fireEvent.click(screen.getByTestId('to-step3-btn')); // → step 3
    expect(screen.getByTestId('aggregate-display')).toBeInTheDocument();
    expect(screen.getByTestId('aggregate-display')).toHaveTextContent('Alice');
  });

  // ── Pol.is section ──────────────────────────────────────────────────────────

  it('calls polis-simulation API on button click', async () => {
    apiClient.POST.mockResolvedValue(makePolisData());
    renderPage();
    fireEvent.click(screen.getByTestId('run-polis-btn'));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));
    expect(apiClient.POST).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/(v2\/)?tech\/polis-simulation/),
      expect.any(Object)
    );
    vi.runAllTimers();
  });

  it('renders Pol.is scatter SVG after run', async () => {
    apiClient.POST.mockResolvedValue(makePolisData());
    renderPage();
    fireEvent.click(screen.getByTestId('run-polis-btn'));
    await waitFor(() => expect(screen.getByTestId('polis-scatter-svg')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows consensus section when consensus items exist', async () => {
    apiClient.POST.mockResolvedValue(makePolisData());
    renderPage();
    fireEvent.click(screen.getByTestId('run-polis-btn'));
    await waitFor(() => expect(screen.getByTestId('consensus-section')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows polarizing section when polarizing items exist', async () => {
    apiClient.POST.mockResolvedValue(makePolisData());
    renderPage();
    fireEvent.click(screen.getByTestId('run-polis-btn'));
    await waitFor(() => expect(screen.getByTestId('polarizing-section')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows cluster vote table', async () => {
    apiClient.POST.mockResolvedValue(makePolisData());
    renderPage();
    fireEvent.click(screen.getByTestId('run-polis-btn'));
    await waitFor(() => expect(screen.getByTestId('cluster-vote-table')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows blockchain comparison table', () => {
    renderPage();
    // Blockchain table is static — always present
    expect(screen.getByTestId('blockchain-table-section')).toBeInTheDocument();
    expect(screen.getByText('Conviction Voting')).toBeInTheDocument();
    expect(screen.getByText('Quadratic Funding')).toBeInTheDocument();
  });

  it('shows error on API failure', async () => {
    apiClient.POST.mockRejectedValue(new Error('Network error'));
    renderPage();
    fireEvent.click(screen.getByTestId('run-polis-btn'));
    await waitFor(() => expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument());
  });
});
