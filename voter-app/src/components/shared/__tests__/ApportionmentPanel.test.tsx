import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import ApportionmentPanel from '../ApportionmentPanel';

jest.mock('axios', () => ({ post: jest.fn() }));
const { post: mockPost } = jest.requireMock('axios') as { post: jest.Mock };

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
        hamilton:        baseResult(alabamaHamilton, false, 'neutral'),
        jefferson:       baseResult(false, true, 'large_parties'),
        webster:         baseResult(false, false, 'neutral'),
        adams:           baseResult(false, false, 'small_parties'),
        huntington_hill: baseResult(false, false, 'neutral'),
      },
      balinski_young_summary: 'Aucune méthode ne peut satisfaire simultanément tous les axiomes.',
      impossible_to_avoid:    ['Quotient strict', 'Monotonie chambre', 'Monotonie population'],
      pedagogical_note:       'Test note.',
    },
  };
}

function renderPanel() {
  return render(<MemoryRouter><ApportionmentPanel /></MemoryRouter>);
}

beforeEach(() => { jest.clearAllMocks(); jest.useFakeTimers(); });
afterEach(() => { jest.useRealTimers(); });

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

  it('calls axios.post on simulate click', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));
    expect(mockPost).toHaveBeenCalledWith(
      expect.stringContaining('/api/theory/apportionment'),
      expect.any(Object),
    );
    jest.runAllTimers();
  });

  it('renders comparison table after data loads', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('comparison-table')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('renders axioms table', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('axioms-table')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows Alabama alert when Hamilton has paradox', async () => {
    mockPost.mockResolvedValue(makeData(true));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('alabama-alert')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('does NOT show Alabama alert when no paradox', async () => {
    mockPost.mockResolvedValue(makeData(false));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => screen.getByTestId('comparison-table'));
    expect(screen.queryByTestId('alabama-alert')).not.toBeInTheDocument();
    jest.runAllTimers();
  });

  it('shows impossibility alert', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('impossibility-alert')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows country comparison table', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('country-table')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows Alabama demo section', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByTestId('alabama-demo')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows error on API failure', async () => {
    mockPost.mockRejectedValue(new Error('Network error'));
    renderPanel();
    fireEvent.click(screen.getByTestId('simulate-btn'));
    await waitFor(() => expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument());
  });
});
