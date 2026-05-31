import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import WhatIfPage, {
  generateValues,
  detectWinnerChanges,
  WinnerChange,
} from './WhatIfPage';
import { WhatIfDataPoint } from '../services/whatIfApi';

// ── Mocks ─────────────────────────────────────────────────────────────────

jest.mock('../hooks/useMetaTags', () => ({ useMetaTags: () => {} }));
jest.mock('../stores/useUIStore', () => ({
  ...jest.requireActual('../stores/useUIStore'),
  useExpertMode: () => ({ expertMode: false }),
}));

// Mock the API service
jest.mock('../services/whatIfApi', () => ({
  ...jest.requireActual('../services/whatIfApi'),
  runWhatIf: jest.fn(),
}));

import { runWhatIf } from '../services/whatIfApi';
const mockRunWhatIf = runWhatIf as jest.MockedFunction<typeof runWhatIf>;

// Sample API response
const MOCK_RESULTS: WhatIfDataPoint[] = [
  {
    value: 200,
    condorcet_winner: 'Alice',
    methods: {
      plurality: { winner: 'Alice', score: 42.5, regret: 0.12 },
      borda:     { winner: 'Alice', score: 55.0, regret: 0.08 },
      irv:       { winner: 'Alice', score: 48.0, regret: 0.10 },
      schulze:   { winner: 'Alice', score: 50.0, regret: 0.09 },
      approval:  { winner: 'Alice', score: 44.0, regret: 0.11 },
    },
  },
  {
    value: 1000,
    condorcet_winner: 'Bob',
    methods: {
      plurality: { winner: 'Alice', score: 40.0, regret: 0.13 },
      borda:     { winner: 'Bob',   score: 52.0, regret: 0.09 }, // Borda changes winner
      irv:       { winner: 'Alice', score: 46.0, regret: 0.11 },
      schulze:   { winner: 'Bob',   score: 49.0, regret: 0.10 }, // Schulze changes winner
      approval:  { winner: 'Alice', score: 41.0, regret: 0.12 },
    },
  },
  {
    value: 5000,
    condorcet_winner: 'Bob',
    methods: {
      plurality: { winner: 'Alice', score: 39.0, regret: 0.14 },
      borda:     { winner: 'Bob',   score: 54.0, regret: 0.08 },
      irv:       { winner: 'Bob',   score: 47.0, regret: 0.10 }, // IRV changes winner
      schulze:   { winner: 'Bob',   score: 51.0, regret: 0.09 },
      approval:  { winner: 'Bob',   score: 43.0, regret: 0.11 }, // Approval changes winner
    },
  },
];

// ── generateValues ─────────────────────────────────────────────────────────

describe('generateValues', () => {
  it('generates N evenly spaced values', () => {
    const vals = generateValues(0, 10, 6);
    expect(vals).toHaveLength(6);
    expect(vals[0]).toBe(0);
    expect(vals[5]).toBe(10);
  });

  it('generates a single value when n=1', () => {
    expect(generateValues(5, 10, 1)).toEqual([5]);
  });

  it('handles floating-point ranges without precision noise', () => {
    const vals = generateValues(0, 0.5, 6);
    expect(vals[0]).toBe(0);
    expect(vals[5]).toBe(0.5);
    vals.forEach((v) => expect(v).toBeLessThanOrEqual(0.501));
  });
});

// ── detectWinnerChanges ────────────────────────────────────────────────────

describe('detectWinnerChanges', () => {
  it('detects no changes when all winners are the same', () => {
    const uniform: WhatIfDataPoint[] = [
      { value: 100, condorcet_winner: 'A', methods: { plurality: { winner: 'A', score: 50, regret: 0 } } },
      { value: 200, condorcet_winner: 'A', methods: { plurality: { winner: 'A', score: 50, regret: 0 } } },
    ];
    expect(detectWinnerChanges(uniform, ['plurality'])).toEqual([]);
  });

  it('detects a winner change between consecutive data points', () => {
    const data: WhatIfDataPoint[] = [
      { value: 200,  condorcet_winner: null, methods: { plurality: { winner: 'Alice', score: 40, regret: 0 } } },
      { value: 1000, condorcet_winner: null, methods: { plurality: { winner: 'Bob',   score: 38, regret: 0 } } },
    ];
    const changes = detectWinnerChanges(data, ['plurality']);
    expect(changes).toHaveLength(1);
    expect(changes[0].from).toBe('Alice');
    expect(changes[0].to).toBe('Bob');
    expect(changes[0].value).toBe(1000);
    expect(changes[0].method).toBe('plurality');
  });

  it('detects multiple method changes in MOCK_RESULTS', () => {
    const changes = detectWinnerChanges(MOCK_RESULTS, ['plurality', 'borda', 'irv', 'schulze', 'approval']);
    // borda: Alice→Bob at index 1
    // schulze: Alice→Bob at index 1
    // irv: Alice→Bob at index 2
    // approval: Alice→Bob at index 2
    const methodsChanged = [...new Set(changes.map((c) => c.method))];
    expect(methodsChanged).toContain('borda');
    expect(methodsChanged).toContain('schulze');
    // Plurality never changes (always Alice)
    expect(methodsChanged).not.toContain('plurality');
  });

  it('returns changes in correct order (by index)', () => {
    const changes = detectWinnerChanges(MOCK_RESULTS, ['plurality', 'borda']);
    changes.forEach((c, i) => {
      if (i > 0) expect(c.valueIndex).toBeGreaterThanOrEqual(changes[i - 1].valueIndex);
    });
  });

  it('handles empty results gracefully', () => {
    expect(detectWinnerChanges([], ['plurality'])).toEqual([]);
  });

  it('handles single result (no change possible)', () => {
    const single: WhatIfDataPoint[] = [
      { value: 100, condorcet_winner: null, methods: { plurality: { winner: 'X', score: 50, regret: 0 } } },
    ];
    expect(detectWinnerChanges(single, ['plurality'])).toEqual([]);
  });
});

// ── WhatIfPage component ───────────────────────────────────────────────────

describe('WhatIfPage — rendering', () => {
  beforeEach(() => {
    mockRunWhatIf.mockReset();
  });

  it('renders page title and configuration panels', () => {
    render(<WhatIfPage />);
    expect(screen.getByRole('heading', { level: 2, name: /Et si/i })).toBeInTheDocument();
    expect(screen.queryAllByText(/Scénario de base/i).length).toBeGreaterThan(0);
    expect(screen.queryAllByText(/Paramètre variable/i).length).toBeGreaterThan(0);
  });

  it('renders all four variant param buttons', () => {
    render(<WhatIfPage />);
    expect(screen.getByRole('button', { name: /électeurs/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /candidats/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Vote blanc/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Polarisation/i })).toBeInTheDocument();
  });

  it('shows info alert when no results yet', () => {
    render(<WhatIfPage />);
    expect(screen.getByText(/Configurez le scénario/i)).toBeInTheDocument();
  });

  it('disables the correct slider when num_voters is selected', () => {
    render(<WhatIfPage />);
    // num_voters param is selected by default
    const voterSlider = screen.getByRole('slider', { name: /lecteurs.*\d+/i });
    expect(voterSlider).toBeDisabled();
  });

  it('clicking "Nombre de candidats" button selects it (aria-pressed)', () => {
    render(<WhatIfPage />);
    const candBtn = screen.getByRole('button', { name: /Nombre de candidats/i });
    fireEvent.click(candBtn);
    expect(candBtn).toHaveAttribute('aria-pressed', 'true');
  });
});

describe('WhatIfPage — API integration', () => {
  beforeEach(() => {
    mockRunWhatIf.mockReset();
  });

  it('calls runWhatIf with correct params and shows chart after response', async () => {
    mockRunWhatIf.mockResolvedValue({
      variant_param: 'num_voters',
      results: MOCK_RESULTS,
    });

    render(<WhatIfPage />);
    fireEvent.click(screen.getByRole('button', { name: /Lancer/i }));

    // Merge both assertions into one waitFor so the act() wrapper covers both
    await waitFor(() => {
      expect(mockRunWhatIf).toHaveBeenCalledWith(
        expect.objectContaining({ variant_param: 'num_voters' }),
      );
      expect(screen.getByText(/Score de majorité/i)).toBeInTheDocument();
    });
  });

  it('shows divergence alert when methods elect different winners', async () => {
    mockRunWhatIf.mockResolvedValue({
      variant_param: 'num_voters',
      results: MOCK_RESULTS,
    });

    render(<WhatIfPage />);
    fireEvent.click(screen.getByRole('button', { name: /Lancer/i }));

    await waitFor(() => {
      expect(screen.getByText(/Divergence/i)).toBeInTheDocument();
    });
  });

  it('renders the data table with winner names', async () => {
    mockRunWhatIf.mockResolvedValue({
      variant_param: 'num_voters',
      results: MOCK_RESULTS,
    });

    render(<WhatIfPage />);
    fireEvent.click(screen.getByRole('button', { name: /Lancer/i }));

    await waitFor(() => {
      // Alice appears in the results table (she wins plurality)
      expect(screen.getAllByText('Alice').length).toBeGreaterThan(0);
    });
  });

  it('shows error alert when API fails', async () => {
    mockRunWhatIf.mockRejectedValue({
      response: { data: { error: 'Backend error' } },
      message: 'Backend error',
    });

    render(<WhatIfPage />);
    fireEvent.click(screen.getByRole('button', { name: /Lancer/i }));

    await waitFor(() => {
      expect(screen.getByText(/Backend error/i)).toBeInTheDocument();
    });
  });

  it('shows loading spinner during request', async () => {
    let resolve: (v: any) => void = () => {};
    mockRunWhatIf.mockImplementation(
      () => new Promise((r) => { resolve = r; }),
    );

    render(<WhatIfPage />);
    fireEvent.click(screen.getByRole('button', { name: /Lancer/i }));

    // Spinner should appear while loading
    expect(screen.getByText(/Analyse en cours/i)).toBeInTheDocument();

    // Resolve promise to clean up
    resolve({ variant_param: 'num_voters', results: [] });
  });
});
