import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import ApportionmentPanel from '../ApportionmentPanel';
import { makeTestQueryClient } from '../../../test/queryWrapper';

vi.mock('../../../api/client', () => ({
  apiClient: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn(), PATCH: vi.fn() },
  getAccessToken: vi.fn(() => null),
}));
const { apiClient } = (await import('../../../api/client')) as unknown as {
  apiClient: { POST: jest.Mock };
};

function makeData(alabamaHamilton = true) {
  const baseResult = (al: boolean, qv: boolean, favors: string) => ({
    seats: { A: 4, B: 3, C: al ? 2 : 3 },
    quota_violation: qv,
    alabama_paradox: al,
    population_paradox: false,
    new_state_paradox: false,
    favors,
    description: 'Test description',
  });
  return {
    data: {
      results: {
        hamilton: baseResult(alabamaHamilton, false, 'neutral'),
        jefferson: baseResult(false, true, 'large_parties'),
        webster: baseResult(false, false, 'neutral'),
        adams: baseResult(false, false, 'small_parties'),
        huntington_hill: baseResult(false, false, 'neutral'),
      },
      balinski_young_summary: 'Aucune méthode ne peut satisfaire simultanément tous les axiomes.',
      impossible_to_avoid: ['Quotient strict', 'Monotonie chambre', 'Monotonie population'],
      pedagogical_note: 'Test note.',
    },
    error: undefined,
  };
}

function renderPanel() {
  return render(
    <MemoryRouter>
      <QueryClientProvider client={makeTestQueryClient()}>
        <ApportionmentPanel />
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

describe('ApportionmentPanel', () => {
  it('shows simulate button', () => {
    renderPanel();
    expect(screen.getByTestId('simulate-btn')).toBeInTheDocument();
  });

  it('shows seats slider', () => {
    renderPanel();
    expect(screen.getByTestId('seats-slider')).toBeInTheDocument();
  });

  it('shows prompt before first run', () => {
    renderPanel();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('calls API on simulate click', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));
    expect(apiClient.POST).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/(v2\/)?theory\/apportionment/),
      expect.any(Object)
    );
    vi.runAllTimers();
  });

  it('renders comparison table after data loads', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('comparison-table')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('renders axioms table', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('axioms-table')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows Alabama alert when Hamilton has paradox', async () => {
    apiClient.POST.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('alabama-alert')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('does NOT show Alabama alert when no paradox', async () => {
    apiClient.POST.mockResolvedValue(makeData(false));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => screen.getByTestId('comparison-table'));
    expect(screen.queryByTestId('alabama-alert')).not.toBeInTheDocument();
    vi.runAllTimers();
  });

  it('shows impossibility alert', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('impossibility-alert')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows country comparison table', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('country-table')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows Alabama demo section', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('alabama-demo')).toBeInTheDocument());
    vi.runAllTimers();
  });

  it('shows error on API failure', async () => {
    apiClient.POST.mockRejectedValue(new Error('Network error'));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument());
  });
});
