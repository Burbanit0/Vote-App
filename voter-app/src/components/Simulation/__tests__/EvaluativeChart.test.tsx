import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import EvaluativeChart, { type EvaluativeResult } from '../EvaluativeChart';

// ── Fixtures ──────────────────────────────────────────────────────────────────

function makeResult(winner = 'Alice'): EvaluativeResult {
  return {
    winner,
    scores: { Alice: 30, Bob: -5, Carol: 10 },
    ev_distribution: {
      Alice: { '+1': 40, '0': 10, '-1': 10 },
      Bob: { '+1': 15, '0': 20, '-1': 25 },
      Carol: { '+1': 25, '0': 20, '-1': 5 },
    },
  };
}

function render_chart(props?: Partial<React.ComponentProps<typeof EvaluativeChart>>) {
  return render(
    <MemoryRouter>
      <EvaluativeChart evResult={makeResult()} candidates={['Alice', 'Bob', 'Carol']} {...props} />
    </MemoryRouter>
  );
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('EvaluativeChart', () => {
  it('renders the chart container', () => {
    render_chart();
    expect(screen.getByTestId('evaluative-chart')).toBeInTheDocument();
  });

  it('renders the SVG', () => {
    render_chart();
    expect(screen.getByTestId('ev-svg')).toBeInTheDocument();
  });

  it('renders winner badge with correct name', () => {
    render_chart();
    const badge = screen.getByTestId('ev-winner-badge');
    expect(badge.textContent).toContain('Alice');
  });

  it('renders one row per candidate', () => {
    const { container } = render_chart();
    expect(container.querySelector('[data-testid="ev-row-Alice"]')).toBeInTheDocument();
    expect(container.querySelector('[data-testid="ev-row-Bob"]')).toBeInTheDocument();
    expect(container.querySelector('[data-testid="ev-row-Carol"]')).toBeInTheDocument();
  });

  it('winner is rendered first', () => {
    const { container } = render_chart();
    const rows = container.querySelectorAll('[data-testid^="ev-row-"]');
    expect(rows[0].getAttribute('data-testid')).toBe('ev-row-Alice');
  });

  it('renders approve bars for candidates with +1 votes', () => {
    const { container } = render_chart();
    const approveBars = container.querySelectorAll('[data-testid="ev-approve-bar"]');
    expect(approveBars.length).toBeGreaterThan(0);
  });

  it('renders reject bars for candidates with -1 votes', () => {
    const { container } = render_chart();
    const rejectBars = container.querySelectorAll('[data-testid="ev-reject-bar"]');
    expect(rejectBars.length).toBeGreaterThan(0);
  });

  it('renders no winner badge when winner is null', () => {
    const result = makeResult();
    result.winner = null;
    render_chart({ evResult: result });
    expect(screen.queryByTestId('ev-winner-badge')).toBeNull();
  });

  it('returns null for empty candidates', () => {
    const { container } = render_chart({ candidates: [] });
    expect(container.querySelector('[data-testid="evaluative-chart"]')).toBeNull();
  });

  it('sorts candidates: winner first, then by net score desc', () => {
    const { container } = render_chart();
    const rows = Array.from(container.querySelectorAll('[data-testid^="ev-row-"]'));
    const names = rows.map((r) => r.getAttribute('data-testid')!.replace('ev-row-', ''));
    // Alice (winner, +30) · Carol (+10) · Bob (-5)
    expect(names[0]).toBe('Alice');
    expect(names[1]).toBe('Carol');
    expect(names[2]).toBe('Bob');
  });
});
