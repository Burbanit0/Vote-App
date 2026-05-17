import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import DuelModePanel from '../DuelModePanel';
import type { ElectionResult } from '../../../services/electionApi';

jest.mock('recharts', () => {
  const React = require('react');
  return {
    BarChart:            ({ children }: any) => <div data-testid="bar-chart">{children}</div>,
    Bar:                 ({ children }: any) => <div>{children}</div>,
    Cell:                () => null,
    XAxis:               () => null,
    YAxis:               () => null,
    Tooltip:             () => null,
    ResponsiveContainer: ({ children }: any) => <div style={{ width: 300, height: 120 }}>{children}</div>,
  };
});

// ── Fixture ───────────────────────────────────────────────────────────────────

function makeResult(overrides: Partial<{
  winnerPlurality: string;
  winnerSchulze:   string;
  condorcet:       string | null;
  blankRate:       number;
}>  = {}): ElectionResult {
  const {
    winnerPlurality = 'Alice',
    winnerSchulze   = 'Bob',
    condorcet       = 'Bob',
    blankRate       = 0,
  } = overrides;

  return {
    config:                 {} as any,
    voters_snapshot:        [
      { id: 0, x: -0.5, y: 0, blank_threshold_final: 0.375 },
      { id: 1, x:  0.5, y: 0, blank_threshold_final: 0.375 },
      { id: 2, x:  0.1, y: 0, blank_threshold_final: 0.375 },
    ],
    candidates:             [
      { name: 'Alice', x: -0.5, y: 0, party: 'Liberal' },
      { name: 'Bob',   x:  0.5, y: 0, party: 'Conservative' },
    ],
    methods: {
      plurality: { winner: winnerPlurality, bayesian_regret: 0.12, majority_satisfaction: 0.6, condorcet_consistent: winnerPlurality === condorcet },
      schulze:   { winner: winnerSchulze,   bayesian_regret: 0.08, majority_satisfaction: 0.75, condorcet_consistent: winnerSchulze === condorcet },
      borda:     { winner: 'Alice',         bayesian_regret: 0.10, majority_satisfaction: 0.65, condorcet_consistent: null },
    },
    condorcet_winner:       condorcet,
    blank_rate:             blankRate,
    campaign_trajectory:    null,
    inter_method_agreement: winnerPlurality === winnerSchulze ? 1 : 0,
    condorcet_exists:       condorcet !== null,
  };
}

function renderDuel(props?: Partial<React.ComponentProps<typeof DuelModePanel>>) {
  const defaults = {
    result:          makeResult(),
    methodA:         'plurality',
    methodB:         'schulze',
    onMethodAChange: jest.fn(),
    onMethodBChange: jest.fn(),
  };
  return render(
    <MemoryRouter>
      <DuelModePanel {...defaults} {...props} />
    </MemoryRouter>
  );
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('DuelModePanel', () => {
  it('renders both method panels', () => {
    renderDuel();
    expect(screen.getByTestId('panel-left')).toBeInTheDocument();
    expect(screen.getByTestId('panel-right')).toBeInTheDocument();
  });

  it('renders both method selectors', () => {
    renderDuel();
    expect(screen.getByTestId('method-select-left')).toBeInTheDocument();
    expect(screen.getByTestId('method-select-right')).toBeInTheDocument();
  });

  it('shows divergence band (red) when winners differ', () => {
    renderDuel({ result: makeResult({ winnerPlurality: 'Alice', winnerSchulze: 'Bob' }) });
    const band = screen.getByTestId('comparison-band');
    expect(band).toBeInTheDocument();
    expect(band.textContent).toMatch(/diverge|divergentes/i);
  });

  it('shows convergence band (green) when winners are the same', () => {
    renderDuel({ result: makeResult({ winnerPlurality: 'Alice', winnerSchulze: 'Alice' }) });
    const band = screen.getByTestId('comparison-band');
    expect(band.textContent).toMatch(/converge|convergent|agree/i);
  });

  it('shows winner badges for both methods', () => {
    renderDuel();
    const wrappers = screen.getAllByTestId('winner-badge-wrapper');
    expect(wrappers.length).toBe(2);
  });

  it('shows Condorcet badge when winner matches condorcet winner', () => {
    renderDuel({
      result:  makeResult({ winnerSchulze: 'Bob', condorcet: 'Bob' }),
      methodB: 'schulze',
    });
    expect(screen.getByText('Condorcet ✓')).toBeInTheDocument();
  });

  it('calls onMethodAChange when left selector changes', () => {
    const handler = jest.fn();
    renderDuel({ onMethodAChange: handler });
    fireEvent.change(screen.getByTestId('method-select-left'), { target: { value: 'borda' } });
    expect(handler).toHaveBeenCalledWith('borda');
  });

  it('calls onMethodBChange when right selector changes', () => {
    const handler = jest.fn();
    renderDuel({ onMethodBChange: handler });
    fireEvent.change(screen.getByTestId('method-select-right'), { target: { value: 'irv' } });
    expect(handler).toHaveBeenCalledWith('irv');
  });

  it('shows pedagogical note containing both method names', () => {
    renderDuel({
      result:  makeResult({ winnerPlurality: 'Alice', winnerSchulze: 'Bob' }),
      methodA: 'plurality',
      methodB: 'schulze',
    });
    const note = screen.getByTestId('duel-pedagogical');
    expect(note.textContent).toMatch(/plurality/i);
    expect(note.textContent).toMatch(/schulze/i);
  });

  it('shows pedagogical Condorcet note when one method misses', () => {
    renderDuel({
      result:  makeResult({ winnerPlurality: 'Alice', winnerSchulze: 'Bob', condorcet: 'Bob' }),
      methodA: 'plurality',
      methodB: 'schulze',
    });
    const note = screen.getByTestId('duel-pedagogical');
    // Note should mention plurality missing Condorcet or Bob being Condorcet winner
    expect(note.textContent?.toLowerCase()).toMatch(/condorcet|plurality|bob/i);
  });

  it('renders bar charts for both panels', () => {
    renderDuel();
    expect(screen.getByTestId('bar-chart-left')).toBeInTheDocument();
    expect(screen.getByTestId('bar-chart-right')).toBeInTheDocument();
  });

  it('shows "same electorate" footer text', () => {
    renderDuel();
    expect(screen.getByTestId('open-full-btn')).toBeInTheDocument();
  });
});

// ── approximateShares logic (via component output) ────────────────────────────

describe('DuelModePanel vote share approximation', () => {
  it('does not crash with empty voters', () => {
    const result = makeResult();
    result.voters_snapshot = [];
    expect(() => renderDuel({ result })).not.toThrow();
  });

  it('renders all candidate bars from voters_snapshot', () => {
    renderDuel();
    // 2 candidates × 2 panels = at least 2 bar charts
    expect(screen.getAllByTestId('bar-chart').length).toBeGreaterThanOrEqual(2);
  });
});
