import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import MethodRaceBar, { sortMethods, type MethodRow } from '../MethodRaceBar';
import MonteCarloRaceChart from '../MonteCarloRaceChart';
import { MethodStreamStats } from '../../../hooks/useMonteCarloStream';

// ── Helpers ───────────────────────────────────────────────────────────────────

function makeStats(winner: string, winnerPct: number, others: string[] = []): MethodStreamStats {
  const dist: Record<string, number> = { [winner]: winnerPct };
  others.forEach((o, i) => { dist[o] = (1 - winnerPct) / (i + 1); });
  return { winner_distribution: dist, most_common_winner: winner };
}

const FIVE_METHODS: Record<string, MethodStreamStats> = {
  plurality:   makeStats('Alice', 0.72),
  borda:       makeStats('Carol', 0.55),
  irv:         makeStats('Alice', 0.61),
  schulze:     makeStats('Carol', 0.48),
  approval:    makeStats('Bob',   0.35),
};

function renderBar(props?: Partial<React.ComponentProps<typeof MethodRaceBar>>) {
  return render(
    <MemoryRouter>
      <MethodRaceBar
        partialResults={FIVE_METHODS}
        isRunning={false}
        {...props}
      />
    </MemoryRouter>
  );
}

// ── Unit: sortMethods ─────────────────────────────────────────────────────────

describe('sortMethods', () => {
  it('returns one row per method', () => {
    const rows = sortMethods(FIVE_METHODS);
    expect(rows.length).toBe(5);
  });

  it('sorts descending by stability', () => {
    const rows = sortMethods(FIVE_METHODS);
    for (let i = 1; i < rows.length; i++) {
      expect(rows[i - 1].stability).toBeGreaterThanOrEqual(rows[i].stability);
    }
  });

  it('rank=0 for the most stable method', () => {
    const rows = sortMethods(FIVE_METHODS);
    expect(rows[0].rank).toBe(0);
  });

  it('rank is sequential', () => {
    const rows = sortMethods(FIVE_METHODS);
    const ranks = rows.map((r) => r.rank).sort((a, b) => a - b);
    expect(ranks).toEqual([0, 1, 2, 3, 4]);
  });

  it('stability equals winner_distribution[most_common_winner]', () => {
    const rows = sortMethods(FIVE_METHODS);
    const plurality = rows.find((r) => r.method === 'plurality')!;
    expect(plurality.stability).toBeCloseTo(0.72, 2);
    expect(plurality.winner).toBe('Alice');
  });

  it('empty input returns empty array', () => {
    expect(sortMethods({})).toEqual([]);
  });
});

// ── Component: MethodRaceBar ──────────────────────────────────────────────────

describe('MethodRaceBar', () => {
  it('renders SVG element', () => {
    renderBar();
    expect(screen.getByTestId('method-race-svg')).toBeInTheDocument();
  });

  it('renders 5 method bar rows for 5 methods', () => {
    const { container } = renderBar();
    const rows = container.querySelectorAll('[data-testid="method-bar-row"]');
    expect(rows.length).toBe(5);
  });

  it('renders one bar-fill per method', () => {
    const { container } = renderBar();
    const fills = container.querySelectorAll('[data-testid="bar-fill"]');
    expect(fills.length).toBe(5);
  });

  it('bar widths are proportional to stability', () => {
    const { container } = renderBar();
    const fills = container.querySelectorAll<SVGRectElement>('[data-testid="bar-fill"]');
    // Extract data-method and width from each fill
    const rows: { method: string; width: number }[] = [];
    fills.forEach((el) => {
      const method = el.getAttribute('data-method') ?? '';
      const width  = parseFloat(el.getAttribute('width') ?? '0');
      rows.push({ method, width });
    });
    // plurality (0.72) should have a wider bar than approval (0.35)
    const plurality = rows.find((r) => r.method === 'plurality')!;
    const approval  = rows.find((r) => r.method === 'approval')!;
    expect(plurality.width).toBeGreaterThan(approval.width);
  });

  it('most stable method has rank 0 (topmost translateY)', () => {
    const { container } = renderBar();
    const rows = container.querySelectorAll<SVGGElement>('[data-testid="method-bar-row"]');
    // Find the plurality row (most stable at 0.72)
    const pluralityRow = Array.from(rows).find(
      (el) => el.getAttribute('data-method') === 'plurality',
    );
    // Its transform should be translateY(16px) — rank 0, y = 0*ROW_H + 16 = 16
    const transform = pluralityRow?.style.transform ?? '';
    expect(transform).toContain('translateY(16px)');
  });

  it('renders stable-badge when a method exceeds 80% (none in fixture)', () => {
    // No method in FIVE_METHODS exceeds 80% — badges should not appear
    renderBar({ isRunning: false });
    const badges = screen.queryAllByTestId(/stable-badge-/);
    expect(badges.length).toBe(0);
  });

  it('shows stable badge when stability >= 80%', () => {
    const highStability: Record<string, MethodStreamStats> = {
      schulze: makeStats('Alice', 0.92),
    };
    render(
      <MemoryRouter>
        <MethodRaceBar partialResults={highStability} isRunning={false} />
      </MemoryRouter>
    );
    expect(screen.getByTestId('stable-badge-schulze')).toBeInTheDocument();
  });

  it('returns null when partialResults is empty', () => {
    const { container } = render(
      <MemoryRouter>
        <MethodRaceBar partialResults={{}} isRunning={false} />
      </MemoryRouter>
    );
    expect(container.firstChild).toBeNull();
  });
});

// ── Integration: toggle in MonteCarloRaceChart ────────────────────────────────

describe('MonteCarloRaceChart method race toggle', () => {
  const baseProps = {
    regretHistory:        {},
    iterationCheckpoints: [50, 100],
    partialResults:       FIVE_METHODS,
    isRunning:            false,
  };

  it('renders without crash with defaultView=candidates', () => {
    render(
      <MemoryRouter>
        <MonteCarloRaceChart {...baseProps} defaultView="candidates" />
      </MemoryRouter>
    );
    expect(screen.getByTestId('view-methods-race')).toBeInTheDocument();
  });

  it('shows MethodRaceBar when methods-race button is clicked', () => {
    const { container } = render(
      <MemoryRouter>
        <MonteCarloRaceChart {...baseProps} />
      </MemoryRouter>
    );
    fireEvent.click(screen.getByTestId('view-methods-race'));
    expect(container.querySelector('[data-testid="method-race-svg"]')).toBeInTheDocument();
  });

  it('switches back to candidate area chart when candidates button clicked', () => {
    const { container } = render(
      <MemoryRouter>
        <MonteCarloRaceChart {...baseProps} />
      </MemoryRouter>
    );
    // Switch to methods view then back
    fireEvent.click(screen.getByTestId('view-methods-race'));
    fireEvent.click(screen.getByTestId('view-candidates'));
    // MethodRaceBar SVG should be gone
    expect(container.querySelector('[data-testid="method-race-svg"]')).toBeNull();
  });

  it('renders with defaultView=methods (starts in methods-race mode)', () => {
    const { container } = render(
      <MemoryRouter>
        <MonteCarloRaceChart {...baseProps} defaultView="methods" />
      </MemoryRouter>
    );
    expect(container.querySelector('[data-testid="method-race-svg"]')).toBeInTheDocument();
  });
});
