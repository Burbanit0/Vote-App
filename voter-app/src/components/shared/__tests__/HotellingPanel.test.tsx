import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import HotellingPanel from '../HotellingPanel';
import { ElectionProvider } from '../../../context/ElectionContext';
import { makeTestQueryClient } from '../../../test/queryWrapper';

jest.mock('../../../api/client', () => ({
  apiClient: { GET: jest.fn(), POST: jest.fn(), PUT: jest.fn(), DELETE: jest.fn(), PATCH: jest.fn() },
  getAccessToken: jest.fn(() => null),
}));
const { apiClient } = jest.requireMock('../../../api/client') as { apiClient: { POST: jest.Mock } };

// ── Fixture ───────────────────────────────────────────────────────────────────

function makeIteration(step: number, ax: number, bx: number, converged: string[] = []) {
  return {
    step,
    candidates: [
      { name: 'Alice', x: ax, y: 0.0 },
      { name: 'Bob',   x: bx, y: 0.0 },
    ],
    scores:               { Alice: 0.5, Bob: 0.5 },
    converged_candidates: converged,
  };
}

function makeData(eqType = 'center_convergence') {
  return {
    data: {
      iterations: [
        makeIteration(0, -0.5,  0.5),
        makeIteration(1, -0.3,  0.3),
        makeIteration(2, -0.1,  0.1),
        makeIteration(3,  0.0,  0.0, ['Alice', 'Bob']),
      ],
      converged:        true,
      convergence_step: 3,
      final_positions:  [{ name: 'Alice', x: 0.0, y: 0.0 }, { name: 'Bob', x: 0.0, y: 0.0 }],
      equilibrium_type: eqType,
      voters:           Array.from({ length: 50 }, (_, i) => ({ x: (i - 25) / 25, y: 0 })),
      candidates:       ['Alice', 'Bob'],
      method:           'plurality',
    },
    error: undefined,
  };
}

function renderPanel() {
  return render(
    <MemoryRouter>
      <QueryClientProvider client={makeTestQueryClient()}>
        <ElectionProvider>
          <HotellingPanel />
        </ElectionProvider>
      </QueryClientProvider>
    </MemoryRouter>
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
  jest.useFakeTimers();
});

afterEach(() => { jest.useRealTimers(); });

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('HotellingPanel', () => {
  it('shows simulate button', () => {
    renderPanel();
    expect(screen.getByRole('button', { name: /simuler|simulate/i })).toBeInTheDocument();
  });

  it('shows prompt before running', () => {
    renderPanel();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('calls API on simulate click', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(apiClient.POST).toHaveBeenCalledTimes(1));
    expect(apiClient.POST).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/(v2\/)?election\/hotelling/),
      expect.any(Object),
    );
    jest.runAllTimers();
  });

  it('renders SVG canvas after data loads', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('hotelling-svg')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('renders trajectory polylines', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    const { container } = renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      const polylines = container.querySelectorAll('[data-testid^="trajectory-"]');
      expect(polylines.length).toBeGreaterThan(0);
    });
    jest.runAllTimers();
  });

  it('shows convergence badge when converged', async () => {
    apiClient.POST.mockResolvedValue(makeData('center_convergence'));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      const badge = screen.getByTestId('convergence-badge');
      expect(badge.textContent).toMatch(/convergence|converged/i);
    });
    jest.runAllTimers();
  });

  it('shows no-convergence badge when not converged', async () => {
    const data = makeData('unstable');
    data.data.converged        = false;
    data.data.convergence_step = null as any;
    apiClient.POST.mockResolvedValue(data);
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => {
      const badge = screen.getByTestId('convergence-badge');
      expect(badge.className).toContain('bg-danger');
    });
    jest.runAllTimers();
  });

  it('step slider navigates through iterations', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('step-slider')).toBeInTheDocument());
    fireEvent.change(screen.getByTestId('step-slider'), { target: { value: '2' } });
    // No crash — step 2 should be displayed
    expect(screen.getByTestId('hotelling-svg')).toBeInTheDocument();
    jest.runAllTimers();
  });

  it('shows play button', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('play-button')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows pedagogical message', async () => {
    apiClient.POST.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByTestId('pedagogical-msg')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('shows error on API failure', async () => {
    apiClient.POST.mockRejectedValue(new Error('Network error'));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /simuler|simulate/i }));
    await waitFor(() => expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument());
  });
});
