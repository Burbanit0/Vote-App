import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import PolarizationPanel from '../PolarizationPanel';
import { ElectionProvider } from '../../../context/ElectionContext';

jest.mock('axios', () => ({ post: jest.fn() }));
const { post: mockPost } = jest.requireMock('axios') as { post: jest.Mock };

jest.mock('recharts', () => {
  const React = require('react');
  return {
    ScatterChart:        ({ children }: any) => <div data-testid="scatter-chart">{children}</div>,
    Scatter:             ({ name }: any) => <div data-testid={`scatter-${name}`} />,
    XAxis:               () => null,
    YAxis:               () => null,
    CartesianGrid:       () => null,
    Tooltip:             () => null,
    Label:               () => null,
    ResponsiveContainer: ({ children }: any) => <div style={{ width: 400, height: 260 }}>{children}</div>,
  };
});

// ── Fixture ───────────────────────────────────────────────────────────────────

function makeData() {
  return {
    data: {
      results: [
        {
          ideology:           'centrist',
          polarization_index: 0.12,
          condorcet_rate:     0.90,
          agreement_rate:     0.85,
          winner_stability:   0.15,
          best_method:        'schulze',
          worst_method:       'plurality',
          method_regrets:     { plurality: 0.089, schulze: 0.031, borda: 0.045 },
        },
        {
          ideology:           'polarized',
          polarization_index: 0.48,
          condorcet_rate:     0.35,
          agreement_rate:     0.42,
          winner_stability:   0.72,
          best_method:        'schulze',
          worst_method:       'plurality',
          method_regrets:     { plurality: 0.134, schulze: 0.062, borda: 0.091 },
        },
      ],
      key_findings: [
        'À partir de P ≈ 0.48, le vainqueur de Condorcet disparaît dans 65% des cas.',
        'Schulze est la méthode la plus robuste dans les électorats polarisés.',
      ],
    },
  };
}

function renderPanel() {
  return render(
    <MemoryRouter>
      <ElectionProvider>
        <PolarizationPanel />
      </ElectionProvider>
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

describe('PolarizationPanel', () => {
  it('shows compute button', () => {
    renderPanel();
    expect(screen.getByRole('button', { name: /calculer|compute/i })).toBeInTheDocument();
  });

  it('shows prompt before running', () => {
    renderPanel();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('shows ideology badges', () => {
    renderPanel();
    expect(screen.getByTestId('ideology-badge-centrist')).toBeInTheDocument();
    expect(screen.getByTestId('ideology-badge-polarized')).toBeInTheDocument();
  });

  it('clicking an ideology badge toggles it', () => {
    renderPanel();
    const badge = screen.getByTestId('ideology-badge-centrist');
    fireEvent.click(badge);
    // Second click re-adds it
    fireEvent.click(badge);
    expect(badge).toBeInTheDocument();
  });

  it('calls axios.post on compute click', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /calculer|compute/i }));
    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));
    expect(mockPost).toHaveBeenCalledWith(
      expect.stringContaining('/api/election/polarization'),
      expect.any(Object),
    );
    jest.runAllTimers();
  });

  it('renders scatter chart after data loads', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /calculer|compute/i }));
    await waitFor(() => expect(screen.getByTestId('scatter-chart')).toBeInTheDocument());
    jest.runAllTimers();
  });

  it('renders one Scatter component per ideology', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /calculer|compute/i }));
    await waitFor(() => {
      expect(screen.getByTestId('scatter-centrist')).toBeInTheDocument();
      expect(screen.getByTestId('scatter-polarized')).toBeInTheDocument();
    });
    jest.runAllTimers();
  });

  it('renders heatmap SVG with cells', async () => {
    mockPost.mockResolvedValue(makeData());
    const { container } = renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /calculer|compute/i }));
    await waitFor(() => {
      expect(screen.getByTestId('polarization-heatmap')).toBeInTheDocument();
      const cells = container.querySelectorAll('[data-testid="heatmap-cell"]');
      expect(cells.length).toBeGreaterThan(0);
    });
    jest.runAllTimers();
  });

  it('shows key findings', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /calculer|compute/i }));
    await waitFor(() => {
      const findings = screen.getAllByTestId('finding-item');
      expect(findings.length).toBe(2);
    });
    jest.runAllTimers();
  });

  it('sims slider triggers debounced API call', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    // Load data first
    fireEvent.click(screen.getByRole('button', { name: /calculer|compute/i }));
    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(1));
    // Move slider → debounce fires after 500ms
    fireEvent.change(screen.getByTestId('sims-slider'), { target: { value: '20' } });
    act(() => { jest.advanceTimersByTime(550); });
    await waitFor(() => expect(mockPost).toHaveBeenCalledTimes(2));
    jest.runAllTimers();
  });

  it('shows best method badge after data loads', async () => {
    mockPost.mockResolvedValue(makeData());
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /calculer|compute/i }));
    await waitFor(() => {
      const badges = screen.getAllByTestId(/best-badge-/);
      expect(badges.length).toBeGreaterThan(0);
    });
    jest.runAllTimers();
  });

  it('shows error on API failure', async () => {
    mockPost.mockRejectedValue(new Error('Network error'));
    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /calculer|compute/i }));
    await waitFor(() => expect(screen.getByText(/Erreur|Error/i)).toBeInTheDocument());
  });
});
