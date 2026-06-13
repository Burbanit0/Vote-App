import { describe, it, expect } from 'vitest';
import {
  ruleWinner,
  ruleWinnerFromRanks,
  fieldWinnerName,
  winRegionGrid,
  sampleVoters,
  RULE_LABELS,
  type NamedPt,
  type Pt,
  type Rule,
} from './playgroundVoting';

// Build a spatial electorate whose 1-D layout reproduces the textbook
// plurality-vs-IRV split: a large bloc nearest A, two smaller blocs whose
// transfers coalesce on C.
function blocs(): { voters: Pt[]; cands: NamedPt[] } {
  const cands: NamedPt[] = [
    { name: 'A', x: -0.9, y: 0 },
    { name: 'B', x: 0.0, y: 0 },
    { name: 'C', x: 0.9, y: 0 },
  ];
  const voters: Pt[] = [];
  const push = (n: number, x: number) => {
    for (let i = 0; i < n; i++) voters.push({ x, y: 0 });
  };
  push(42, -0.95); // nearest A, then B, then C
  push(26, 0.05); //  nearest B, then C
  push(32, 0.92); //  nearest C
  return { voters, cands };
}

describe('playgroundVoting rules', () => {
  it('plurality elects the largest first-preference bloc (A)', () => {
    const { voters, cands } = blocs();
    expect(fieldWinnerName(voters, cands, 'plurality')).toBe('A');
  });

  it('IRV transfers B to C, so C overtakes A', () => {
    const { voters, cands } = blocs();
    // A=42, B=26, C=32 → eliminate B; its 26 go to C (nearer) → C=58 > A=42.
    expect(fieldWinnerName(voters, cands, 'irv')).toBe('C');
  });

  it('a centrist Condorcet winner beats both flanks pairwise', () => {
    const cands: NamedPt[] = [
      { name: 'L', x: -0.8, y: 0 },
      { name: 'M', x: 0.0, y: 0 },
      { name: 'R', x: 0.8, y: 0 },
    ];
    const voters: Pt[] = [];
    for (let i = 0; i < 40; i++) voters.push({ x: -0.7, y: 0 });
    for (let i = 0; i < 25; i++) voters.push({ x: 0.0, y: 0 });
    for (let i = 0; i < 40; i++) voters.push({ x: 0.7, y: 0 });
    // M is nobody's plurality winner but beats L and R head-to-head.
    expect(ruleWinner(voters, cands, 'condorcet')).toBe(1);
    expect(ruleWinner(voters, cands, 'plurality')).not.toBe(1);
  });

  it('winRegionGrid returns a full grid with valid winner indices', () => {
    // Two flanks + a centrist cloud → an entrant in the empty centre wins (entry
    // region non-empty), and every cell maps to a real candidate or the entrant.
    const cands: NamedPt[] = [
      { name: 'L', x: -0.8, y: 0 },
      { name: 'R', x: 0.8, y: 0 },
    ];
    const voters = sampleVoters(200, 1, 'centrist');
    const grid = winRegionGrid(voters, cands, 'plurality', 8);
    expect(grid.n).toBe(8);
    expect(grid.cells).toHaveLength(64);
    expect(grid.cells.every((w) => w >= 0 && w <= cands.length)).toBe(true);
    expect(grid.cells.some((w) => w === cands.length)).toBe(true);
  });
});

describe('extended method set (15 rules)', () => {
  it('every rule has a label and resolves to a winner', () => {
    const cands: NamedPt[] = [
      { name: 'A', x: -0.5, y: 0 },
      { name: 'B', x: 0.0, y: 0.1 },
      { name: 'C', x: 0.5, y: 0 },
    ];
    const voters = sampleVoters(120, 3, 'random');
    for (const rule of Object.keys(RULE_LABELS) as Rule[]) {
      expect(RULE_LABELS[rule]).toBeTruthy();
      const w = ruleWinner(voters, cands, rule);
      expect(w).toBeGreaterThanOrEqual(0);
      expect(w).toBeLessThan(cands.length);
    }
  });

  it('every Condorcet method elects the Condorcet winner; plurality does not', () => {
    // 1-D: M (index 1) beats both flanks pairwise but is nobody's plurality lead.
    const cands: NamedPt[] = [
      { name: 'L', x: -0.8, y: 0 },
      { name: 'M', x: 0.0, y: 0 },
      { name: 'R', x: 0.8, y: 0 },
    ];
    const voters: Pt[] = [];
    for (let i = 0; i < 40; i++) voters.push({ x: -0.7, y: 0 });
    for (let i = 0; i < 25; i++) voters.push({ x: 0.0, y: 0 });
    for (let i = 0; i < 40; i++) voters.push({ x: 0.7, y: 0 });
    for (const rule of ['condorcet', 'minimax', 'schulze', 'nanson', 'baldwin'] as Rule[]) {
      expect(ruleWinner(voters, cands, rule)).toBe(1);
    }
    expect(ruleWinner(voters, cands, 'plurality')).not.toBe(1);
  });

  it('STAR runoff can overturn the score leader', () => {
    // Score leader = B (broad), but A wins the automatic top-2 runoff 6–5.
    const ranks = [...Array(6).fill([0, 1, 2]), ...Array(5).fill([2, 1, 0])];
    const scores = [
      ...Array(6).fill([1.0, 0.8, 0.0]),
      ...Array(5).fill([0.0, 0.6, 1.0]),
    ];
    expect(ruleWinnerFromRanks(ranks, 3, 'score', scores)).toBe(1); // B leads on sum
    expect(ruleWinnerFromRanks(ranks, 3, 'star', scores)).toBe(0); // A wins the runoff
  });

  it('majority judgment ranks by median grade, not mean', () => {
    // A: grades [5,5,0] median 5; B: [4,4,4] median 4 but higher mean.
    const ranks = [[0, 1], [0, 1], [1, 0]];
    const scores = [[1.0, 0.7], [1.0, 0.7], [0.0, 0.7]];
    expect(ruleWinnerFromRanks(ranks, 2, 'majority_judgment', scores)).toBe(0);
    expect(ruleWinnerFromRanks(ranks, 2, 'score', scores)).toBe(1); // mean favours B
  });

  it('Bucklin elects a first-round majority', () => {
    const ranks = [[0, 1, 2], [0, 1, 2], [0, 2, 1], [1, 0, 2], [1, 2, 0]];
    expect(ruleWinnerFromRanks(ranks, 3, 'bucklin', undefined)).toBe(0); // A: 3/5 firsts
  });

  it('Coombs eliminates the most-rejected candidate (≠ plurality)', () => {
    // A leads first prefs but is last for a majority → Coombs elects B.
    const ranks = [
      ...Array(4).fill([0, 1, 2]),
      ...Array(3).fill([1, 2, 0]),
      ...Array(2).fill([2, 1, 0]),
    ];
    expect(ruleWinnerFromRanks(ranks, 3, 'plurality', undefined)).toBe(0);
    expect(ruleWinnerFromRanks(ranks, 3, 'coombs', undefined)).toBe(1);
  });
});

describe('dimensionality (1/2/3-D)', () => {
  it('sampleVoters collapses unused axes and keeps x identical across dims', () => {
    const d1 = sampleVoters(50, 9, 'random', 1);
    const d2 = sampleVoters(50, 9, 'random', 2);
    const d3 = sampleVoters(50, 9, 'random', 3);
    // 1-D: y and z are exactly 0.
    expect(d1.every((p) => p.y === 0 && (p.z ?? 0) === 0)).toBe(true);
    // 2-D: z is 0 but y varies.
    expect(d2.every((p) => (p.z ?? 0) === 0)).toBe(true);
    expect(d2.some((p) => p.y !== 0)).toBe(true);
    // 3-D: z genuinely varies.
    expect(d3.some((p) => (p.z ?? 0) !== 0)).toBe(true);
    // The dimension only ADDS axes — x is the same first draw for all dims.
    expect(d1.map((p) => p.x)).toEqual(d2.map((p) => p.x));
    expect(d2.map((p) => p.x)).toEqual(d3.map((p) => p.x));
  });

  it('distance uses the 3rd axis (a z-separated rival can lose voters)', () => {
    // Two candidates at the same x,y; one offset in z. Voters sit at z=0,
    // so the z=0 candidate wins everyone under plurality.
    const voters: Pt[] = Array.from({ length: 20 }, (_, i) => ({ x: (i - 10) / 20, y: 0, z: 0 }));
    const cands: NamedPt[] = [
      { name: 'Near', x: 0, y: 0, z: 0 },
      { name: 'Far', x: 0, y: 0, z: 0.9 },
    ];
    expect(fieldWinnerName(voters, cands, 'plurality')).toBe('Near');
  });

  it('winRegionGrid is a 1-row strip in 1-D and an n×n grid otherwise', () => {
    const voters = sampleVoters(80, 1, 'random', 1);
    const cands: NamedPt[] = [
      { name: 'L', x: -0.6, y: 0, z: 0 },
      { name: 'R', x: 0.6, y: 0, z: 0 },
    ];
    const g1 = winRegionGrid(voters, cands, 'plurality', 8, 1);
    expect(g1.rows).toBe(1);
    expect(g1.cells).toHaveLength(8);
    const g2 = winRegionGrid(sampleVoters(80, 1, 'random', 2), cands, 'plurality', 8, 2);
    expect(g2.rows).toBe(8);
    expect(g2.cells).toHaveLength(64);
  });
});

describe('sampleVoters', () => {
  it('is deterministic for a fixed seed and stays in [-1,1]²', () => {
    const a = sampleVoters(50, 7, 'random');
    const b = sampleVoters(50, 7, 'random');
    expect(a).toEqual(b);
    expect(a).toHaveLength(50);
    expect(a.every((p) => p.x >= -1 && p.x <= 1 && p.y >= -1 && p.y <= 1)).toBe(true);
  });

  it('polarized produces a wider economic spread than centrist', () => {
    const spread = (pts: Pt[]) => Math.max(...pts.map((p) => p.x)) - Math.min(...pts.map((p) => p.x));
    expect(spread(sampleVoters(400, 1, 'polarized'))).toBeGreaterThan(
      spread(sampleVoters(400, 1, 'centrist'))
    );
  });
});
