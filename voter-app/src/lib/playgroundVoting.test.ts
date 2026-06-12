import { describe, it, expect } from 'vitest';
import {
  ruleWinner,
  fieldWinnerName,
  winRegionGrid,
  sampleVoters,
  type NamedPt,
  type Pt,
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
