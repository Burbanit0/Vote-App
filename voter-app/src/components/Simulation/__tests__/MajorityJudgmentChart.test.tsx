import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import MajorityJudgmentChart, {
  gradeIndex,
  medianLineX,
  type MJResult,
} from '../MajorityJudgmentChart';

// ── Pure helpers ──────────────────────────────────────────────────────────────

describe('gradeIndex', () => {
  const labels = ['À Rejeter', 'Passable', 'Assez Bien', 'Bien', 'Très Bien', 'Excellent'];

  it('returns 0 for first label', () => expect(gradeIndex('À Rejeter', labels)).toBe(0));
  it('returns 5 for last label', () => expect(gradeIndex('Excellent', labels)).toBe(5));
  it('returns 3 for Bien', () => expect(gradeIndex('Bien', labels)).toBe(3));
  it('returns 0 for unknown label', () => expect(gradeIndex('Unknown', labels)).toBe(0));
});

describe('medianLineX', () => {
  it('places line at 50% for symmetric distribution', () => {
    // [10, 10] over 2 grades → median at grade 0 (lower median), x = 50%
    const x = medianLineX([10, 10], 0, 200);
    // grade 0: 10 below (none), at median = 10 → (0 + 5) / 20 * 200 = 50
    expect(x).toBe(50);
  });

  it('returns 0 for empty distribution', () => {
    expect(medianLineX([], 0, 200)).toBe(0);
  });

  it('places line at 100% for full top grade', () => {
    // All in grade 5, median = grade 5, below = all others (0 here), at = total
    const x = medianLineX([0, 0, 0, 0, 0, 20], 5, 200);
    // (0 + 10) / 20 * 200 = 100
    expect(x).toBe(100);
  });
});

// ── Component ─────────────────────────────────────────────────────────────────

function makeResult(winnerName = 'Alice'): MJResult {
  const dist = (
    excellent: number,
    tresB: number,
    bien: number,
    asB: number,
    pass: number,
    rej: number
  ) => [rej, pass, asB, bien, tresB, excellent];

  return {
    winner: winnerName,
    grades: {
      Alice: {
        'À Rejeter': 2,
        Passable: 5,
        'Assez Bien': 10,
        Bien: 20,
        'Très Bien': 30,
        Excellent: 33,
      },
      Bob: {
        'À Rejeter': 10,
        Passable: 15,
        'Assez Bien': 20,
        Bien: 25,
        'Très Bien': 20,
        Excellent: 10,
      },
      Carol: {
        'À Rejeter': 30,
        Passable: 25,
        'Assez Bien': 20,
        Bien: 15,
        'Très Bien': 7,
        Excellent: 3,
      },
    },
    medians: { Alice: 'Très Bien', Bob: 'Bien', Carol: 'Passable' },
    scores: { Alice: 4.07, Bob: 3.1, Carol: 1.9 },
    grade_distributions: {
      Alice: dist(33, 30, 20, 10, 5, 2),
      Bob: dist(10, 20, 25, 20, 15, 10),
      Carol: dist(3, 7, 15, 20, 25, 30),
    },
  };
}

function renderChart(props?: Partial<React.ComponentProps<typeof MajorityJudgmentChart>>) {
  return render(
    <MemoryRouter>
      <MajorityJudgmentChart
        mjResult={makeResult()}
        candidates={['Alice', 'Bob', 'Carol']}
        {...props}
      />
    </MemoryRouter>
  );
}

describe('MajorityJudgmentChart', () => {
  it('renders the chart container', () => {
    renderChart();
    expect(screen.getByTestId('mj-chart')).toBeInTheDocument();
  });

  it('shows winner badge with correct name', () => {
    renderChart();
    const badge = screen.getByTestId('mj-winner-badge');
    expect(badge.textContent).toContain('Alice');
  });

  it('renders one row per candidate', () => {
    renderChart();
    expect(screen.getByTestId('mj-row-Alice')).toBeInTheDocument();
    expect(screen.getByTestId('mj-row-Bob')).toBeInTheDocument();
    expect(screen.getByTestId('mj-row-Carol')).toBeInTheDocument();
  });

  it('winner row is rendered (sorted first)', () => {
    const { container } = renderChart();
    const rows = container.querySelectorAll('[data-testid^="mj-row-"]');
    expect(rows.length).toBe(3);
    // Winner (Alice) should be the first row
    expect(rows[0].getAttribute('data-testid')).toBe('mj-row-Alice');
  });

  it('renders grade segments for each candidate', () => {
    const { container } = renderChart();
    const segments = container.querySelectorAll('[data-testid="mj-grade-segment"]');
    // Up to 6 per candidate, only non-zero ones rendered
    expect(segments.length).toBeGreaterThan(0);
  });

  it('renders median lines', () => {
    const { container } = renderChart();
    const medLines = container.querySelectorAll('[data-testid="mj-median-line"]');
    expect(medLines.length).toBe(3); // one per candidate
  });

  it('renders 6 segments when all grades are present', () => {
    const { container } = renderChart();
    const aliceRow = container.querySelector('[data-testid="mj-row-Alice"]');
    const segments = aliceRow?.querySelectorAll('[data-testid="mj-grade-segment"]');
    // Alice has all 6 grades non-zero
    expect(segments?.length).toBe(6);
  });

  it('shows null / empty state gracefully', () => {
    const empty: MJResult = {
      winner: null,
      grades: {},
      medians: {},
      scores: {},
      grade_distributions: {},
    };
    const { container } = render(
      <MemoryRouter>
        <MajorityJudgmentChart mjResult={empty} candidates={[]} />
      </MemoryRouter>
    );
    // Component returns null — nothing rendered
    expect(container.querySelector('[data-testid="mj-chart"]')).toBeNull();
  });

  it('does not show winner badge when winner is null', () => {
    const result = makeResult();
    result.winner = null;
    renderChart({ mjResult: result });
    expect(screen.queryByTestId('mj-winner-badge')).toBeNull();
  });
});
