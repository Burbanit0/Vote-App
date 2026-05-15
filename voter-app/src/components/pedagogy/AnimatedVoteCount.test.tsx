import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import AnimatedVoteCount, {
  generateSteps,
  generateDemoBallots,
  VoteCandidate,
} from './AnimatedVoteCount';

// ── Test fixtures ───────────────────────────────────────────────────────────

const THREE_CANDIDATES: VoteCandidate[] = [
  { name: 'Alice', color: '#1a56cc' },
  { name: 'Bob',   color: '#b35c00' },
  { name: 'Carol', color: '#b71c1c' },
];

// 10 voters: 5 Alice-first, 3 Bob-first, 2 Carol-first
// indices: Alice=0, Bob=1, Carol=2
const SIMPLE_BALLOTS: number[][] = [
  [0, 1, 2], [0, 1, 2], [0, 1, 2], [0, 1, 2], [0, 1, 2], // 5× Alice first
  [1, 0, 2], [1, 0, 2], [1, 0, 2],                         // 3× Bob first
  [2, 1, 0], [2, 1, 0],                                     // 2× Carol first
];

// ── generateSteps — plurality ───────────────────────────────────────────────

describe('generateSteps — plurality', () => {
  it('returns exactly 1 step', () => {
    const steps = generateSteps('plurality', THREE_CANDIDATES, SIMPLE_BALLOTS);
    expect(steps).toHaveLength(1);
  });

  it('correctly counts first-choice votes', () => {
    const steps = generateSteps('plurality', THREE_CANDIDATES, SIMPLE_BALLOTS);
    expect(steps[0].scores['Alice']).toBe(5);
    expect(steps[0].scores['Bob']).toBe(3);
    expect(steps[0].scores['Carol']).toBe(2);
  });

  it('identifies the winner', () => {
    const steps = generateSteps('plurality', THREE_CANDIDATES, SIMPLE_BALLOTS);
    expect(steps[0].winner).toBe('Alice');
  });

  it('returns 1 step even when winner has no absolute majority', () => {
    // Plurality: no majority required — most votes wins
    const close: number[][] = [[0, 1, 2], [1, 0, 2], [2, 1, 0]]; // 1-1-1 tie, first one wins
    const steps = generateSteps('plurality', THREE_CANDIDATES, close);
    expect(steps).toHaveLength(1);
  });
});

// ── generateSteps — borda ───────────────────────────────────────────────────

describe('generateSteps — borda', () => {
  it('returns exactly 1 step', () => {
    const steps = generateSteps('borda', THREE_CANDIDATES, SIMPLE_BALLOTS);
    expect(steps).toHaveLength(1);
  });

  it('awards n-1 points to first choice, 0 to last', () => {
    const steps = generateSteps('borda', THREE_CANDIDATES, SIMPLE_BALLOTS);
    // Alice: 5×(2pts) + 3×(1pt) + 2×(0pt) = 10 + 3 = 13
    expect(steps[0].scores['Alice']).toBe(13);
    // Bob: 5×(1pt) + 3×(2pt) + 2×(1pt) = 5 + 6 + 2 = 13
    expect(steps[0].scores['Bob']).toBe(13);
    // Carol: 5×(0pt) + 3×(0pt) + 2×(2pt) = 4
    expect(steps[0].scores['Carol']).toBe(4);
  });
});

// ── generateSteps — irv ─────────────────────────────────────────────────────

describe('generateSteps — irv', () => {
  it('eliminates candidate with fewest first-choice votes first', () => {
    const steps = generateSteps('irv', THREE_CANDIDATES, SIMPLE_BALLOTS);
    // Round 1: Alice=5, Bob=3, Carol=2 → Carol eliminated
    const elimStep = steps.find((s) => s.eliminated !== undefined);
    expect(elimStep).toBeDefined();
    expect(elimStep!.eliminated).toBe('Carol');
  });

  it('finds winner once majority is reached', () => {
    // After Carol is eliminated: Alice still has 5, Bob gets 5 (Carol voters → Bob second choice)
    // Total = 10, need > 5 for majority
    const steps = generateSteps('irv', THREE_CANDIDATES, SIMPLE_BALLOTS);
    const winnerStep = steps.find((s) => s.winner !== undefined);
    expect(winnerStep).toBeDefined();
    // Alice has 5/10 = exactly 50% — not majority. Bob gets Carol's 2 votes → Bob=5, Alice=5 (tie)
    // In our implementation: 5 > 10/2 is false (5 > 5 is false)
    // Both tied → Bob or Alice via sort order. Let's just check there IS a winner:
    expect(winnerStep!.winner).toBeDefined();
  });

  it('produces at least 1 step', () => {
    const steps = generateSteps('irv', THREE_CANDIDATES, SIMPLE_BALLOTS);
    expect(steps.length).toBeGreaterThanOrEqual(1);
  });

  it('with a clear majority candidate, stops after 1 round', () => {
    // 7 Alice first-choice out of 10 → immediate majority (>5)
    const ballots: number[][] = [
      [0, 1, 2], [0, 1, 2], [0, 1, 2], [0, 1, 2], [0, 1, 2], [0, 1, 2], // 6× Alice
      [1, 0, 2], [1, 0, 2],                                                 // 2× Bob
      [2, 1, 0], [2, 1, 0],                                                 // 2× Carol
    ];
    const steps = generateSteps('irv', THREE_CANDIDATES, ballots);
    expect(steps[0].winner).toBe('Alice');
    expect(steps[0].title).toMatch(/Majorité/);
  });
});

// ── generateSteps — two-round ───────────────────────────────────────────────

describe('generateSteps — two-round', () => {
  it('returns 1 step when first round majority', () => {
    const ballots = Array.from({ length: 10 }, () => [0, 1, 2] as number[]);
    const steps = generateSteps('two-round', THREE_CANDIDATES, ballots);
    expect(steps).toHaveLength(1);
    expect(steps[0].winner).toBe('Alice');
  });

  it('returns 2 steps when no first-round majority', () => {
    const steps = generateSteps('two-round', THREE_CANDIDATES, SIMPLE_BALLOTS);
    expect(steps).toHaveLength(2);
  });

  it('second step only contains top-2 candidates', () => {
    const steps = generateSteps('two-round', THREE_CANDIDATES, SIMPLE_BALLOTS);
    const r2Keys = Object.keys(steps[1].scores);
    expect(r2Keys).toHaveLength(2);
    // Carol (lowest in round 1) should NOT appear
    expect(r2Keys).not.toContain('Carol');
  });
});

// ── generateSteps — approval ────────────────────────────────────────────────

describe('generateSteps — approval', () => {
  it('returns 1 step', () => {
    const steps = generateSteps('approval', THREE_CANDIDATES, SIMPLE_BALLOTS);
    expect(steps).toHaveLength(1);
  });

  it('approves top ⌈n/2⌉ candidates per ballot', () => {
    // 3 candidates → approve top 2 on each ballot
    const steps = generateSteps('approval', THREE_CANDIDATES, SIMPLE_BALLOTS);
    // Threshold = ceil(3/2) = 2 → top 2 candidates approved per ballot
    // [0,1,2] Alice-first: approve indices 0(Alice) + 1(Bob) → 5 ballots
    // [1,0,2] Bob-first  : approve indices 1(Bob)  + 0(Alice) → 3 ballots
    // [2,1,0] Carol-first: approve indices 2(Carol) + 1(Bob)  → 2 ballots
    // Alice: 5(from Alice-first) + 3(from Bob-first) = 8
    // Bob  : 5(from Alice-first) + 3(from Bob-first) + 2(from Carol-first) = 10
    // Carol: 2(from Carol-first)
    expect(steps[0].scores['Alice']).toBe(8);
    expect(steps[0].scores['Bob']).toBe(10);
    expect(steps[0].scores['Carol']).toBe(2);
  });
});

// ── generateDemoBallots ─────────────────────────────────────────────────────

describe('generateDemoBallots', () => {
  it('returns the requested number of ballots', () => {
    const ballots = generateDemoBallots(['Alice', 'Bob', 'Carol'], 'Alice', 50);
    expect(ballots).toHaveLength(50);
  });

  it('each ballot has all candidate indices exactly once', () => {
    const ballots = generateDemoBallots(['Alice', 'Bob', 'Carol'], 'Alice', 30);
    for (const ballot of ballots) {
      expect(ballot).toHaveLength(3);
      expect([...ballot].sort()).toEqual([0, 1, 2]);
    }
  });

  it('winner appears first in ~45% of ballots', () => {
    const ballots = generateDemoBallots(['Alice', 'Bob', 'Carol'], 'Alice', 100);
    const winnerFirst = ballots.filter((b) => b[0] === 0).length;
    expect(winnerFirst).toBeGreaterThanOrEqual(40);
    expect(winnerFirst).toBeLessThanOrEqual(55);
  });

  it('is deterministic (same output for same inputs)', () => {
    const a = generateDemoBallots(['Alice', 'Bob'], 'Alice', 20);
    const b = generateDemoBallots(['Alice', 'Bob'], 'Alice', 20);
    expect(a).toEqual(b);
  });
});

// ── AnimatedVoteCount component rendering ───────────────────────────────────

describe('AnimatedVoteCount — render', () => {
  it('renders without crashing', () => {
    render(
      <AnimatedVoteCount
        method="plurality"
        candidates={THREE_CANDIDATES}
        ballots={SIMPLE_BALLOTS}
        speed="normal"
      />,
    );
    expect(screen.getByRole('toolbar')).toBeInTheDocument();
  });

  it('shows navigation buttons', () => {
    render(
      <AnimatedVoteCount
        method="plurality"
        candidates={THREE_CANDIDATES}
        ballots={SIMPLE_BALLOTS}
        speed="normal"
      />,
    );
    expect(screen.getByTitle('Début')).toBeInTheDocument();
    expect(screen.getByTitle('Fin')).toBeInTheDocument();
    expect(screen.getByTitle('Auto')).toBeInTheDocument();
  });

  it('shows candidate names', () => {
    render(
      <AnimatedVoteCount
        method="plurality"
        candidates={THREE_CANDIDATES}
        ballots={SIMPLE_BALLOTS}
        speed="normal"
      />,
    );
    // Candidate names appear in multiple places (bar label + description text)
    expect(screen.getAllByText(/Alice/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Bob/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Carol/).length).toBeGreaterThanOrEqual(1);
  });

  it('renders irv with multiple steps without crash', () => {
    render(
      <AnimatedVoteCount
        method="irv"
        candidates={THREE_CANDIDATES}
        ballots={SIMPLE_BALLOTS}
        speed="fast"
      />,
    );
    expect(screen.getByText(/Étape/)).toBeInTheDocument();
  });

  it('renders empty state gracefully when ballots array is empty', () => {
    render(
      <AnimatedVoteCount
        method="plurality"
        candidates={THREE_CANDIDATES}
        ballots={[]}
        speed="normal"
      />,
    );
    expect(screen.getByText(/Pas de données/)).toBeInTheDocument();
  });
});
