import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import MethodSimilarityGraph, {
  flatToMatrix,
  partialResultsToMatrix,
} from '../MethodSimilarityGraph';

// Mock requestAnimationFrame so D3 simulation ticks don't run in jsdom
beforeEach(() => {
  vi.spyOn(global, 'requestAnimationFrame').mockImplementation(() => 1);
  vi.spyOn(global, 'cancelAnimationFrame').mockImplementation(() => {});
});

afterEach(() => {
  vi.restoreAllMocks();
});

// ── Test helpers ──────────────────────────────────────────────────────────────

const FIVE_METHODS = ['plurality', 'borda', 'irv', 'schulze', 'approval'];

function makeMatrix(methods: string[], agreement = 0.75): Record<string, Record<string, number>> {
  const m: Record<string, Record<string, number>> = {};
  for (const a of methods) {
    m[a] = {};
    for (const b of methods) {
      m[a][b] = a === b ? 1 : agreement;
    }
  }
  return m;
}

function renderGraph(props?: Partial<React.ComponentProps<typeof MethodSimilarityGraph>>) {
  return render(
    <MemoryRouter>
      <MethodSimilarityGraph
        agreementMatrix={makeMatrix(FIVE_METHODS)}
        {...props}
      />
    </MemoryRouter>
  );
}

// ── Unit: helper functions ────────────────────────────────────────────────────

describe('flatToMatrix', () => {
  it('converts flat keys to nested matrix', () => {
    const flat = { 'plurality|borda': 0.8, 'borda|irv': 0.65 };
    const mat = flatToMatrix(flat);
    expect(mat['plurality']['borda']).toBe(0.8);
    expect(mat['borda']['plurality']).toBe(0.8);
    expect(mat['borda']['irv']).toBe(0.65);
  });

  it('returns empty object for empty input', () => {
    expect(flatToMatrix({})).toEqual({});
  });
});

describe('partialResultsToMatrix', () => {
  it('computes agreement as overlap of winner distributions', () => {
    const pr = {
      plurality: { winner_distribution: { Alice: 0.7, Bob: 0.3 }, most_common_winner: 'Alice' },
      borda:     { winner_distribution: { Alice: 0.7, Bob: 0.3 }, most_common_winner: 'Alice' },
    };
    const mat = partialResultsToMatrix(pr);
    expect(mat['plurality']['borda']).toBeCloseTo(1.0, 1); // identical distributions
    expect(mat['plurality']['plurality']).toBe(1.0);
  });

  it('gives 0 when distributions are disjoint', () => {
    const pr = {
      plurality: { winner_distribution: { Alice: 1.0 }, most_common_winner: 'Alice' },
      borda:     { winner_distribution: { Bob:   1.0 }, most_common_winner: 'Bob'   },
    };
    const mat = partialResultsToMatrix(pr);
    expect(mat['plurality']['borda']).toBe(0);
  });
});

// ── Component rendering ───────────────────────────────────────────────────────

describe('MethodSimilarityGraph', () => {
  it('renders the SVG graph container', () => {
    renderGraph();
    expect(screen.getByTestId('similarity-graph')).toBeInTheDocument();
  });

  it('renders N nodes for N methods (5)', () => {
    const { container } = renderGraph();
    const nodes = container.querySelectorAll('[data-testid="graph-node"]');
    expect(nodes.length).toBe(FIVE_METHODS.length);
  });

  it('renders edges when threshold is below agreement (0.75)', () => {
    const { container } = renderGraph();
    const edges = container.querySelectorAll('[data-testid="graph-edge"]');
    // 5 methods, 10 unique pairs, all agree at 0.75 > threshold 0.6
    expect(edges.length).toBe(10);
  });

  it('threshold slider at 1.0 → 0 edges', () => {
    const { container } = renderGraph();
    fireEvent.change(screen.getByTestId('threshold-slider'), { target: { value: '1.0' } });
    const edges = container.querySelectorAll('[data-testid="graph-edge"]');
    expect(edges.length).toBe(0);
  });

  it('threshold slider at 0.0 → N*(N-1)/2 edges', () => {
    const { container } = renderGraph();
    fireEvent.change(screen.getByTestId('threshold-slider'), { target: { value: '0' } });
    const n = FIVE_METHODS.length;
    const edges = container.querySelectorAll('[data-testid="graph-edge"]');
    expect(edges.length).toBe((n * (n - 1)) / 2);
  });

  it('shows noData message for empty matrix', () => {
    renderGraph({ agreementMatrix: {} });
    // With no methods, the noData text (i18n key or translation) is shown
    expect(screen.getByText(/noData|Aucune|No agreement/i)).toBeInTheDocument();
  });

  it('group-by-family button toggles', () => {
    renderGraph();
    const btn = screen.getByTestId('group-by-family-btn');
    expect(btn).toBeInTheDocument();
    fireEvent.click(btn);
    expect(btn.className).toContain('btn-secondary');
  });

  it.skip('shows hover tooltip when hovering a node', () => {
    // ⚠ The graph uses Pointer Events + D3 force simulation, neither of which
    // settle deterministically in jsdom. Skipped until we wire a force
    // simulation seed for tests or migrate to a different hover trigger.
    const { container } = renderGraph();
    const circles = container.querySelectorAll('[data-testid="graph-node"] circle');
    if (circles.length > 0) {
      fireEvent.mouseEnter(circles[0]);
      const tooltip = container.querySelector('[data-testid="hover-tooltip"]');
      expect(tooltip).toBeInTheDocument();
    }
  });
});
