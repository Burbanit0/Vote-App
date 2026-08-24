import { describe, it, expect } from 'vitest';
import {
  ruleWinner,
  ruleWinnerFromRanks,
  condorcetWinnerIdx,
  fieldWinnerName,
  winRegionGrid,
  randomBallotShares,
  randomBallotProbGrid,
  sampleVoters,
  applyTurnout,
  applyBlankVote,
  smithSet,
  RULE_LABELS,
  type NamedPt,
  type Pt,
  type Rule,
} from './playgroundVoting';

/** Expand grouped ballots ([count, ranking]) into a flat ranks array. */
function ranksOf(groups: [number, number[]][]): number[][] {
  const out: number[][] = [];
  for (const [n, r] of groups) for (let i = 0; i < n; i++) out.push(r.slice());
  return out;
}

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

describe('Tier B extras (client-only)', () => {
  // B (index 1) is the Condorcet winner: beats A 5–4 and C 7–2.
  const cw = ranksOf([
    [4, [0, 1, 2]],
    [3, [1, 2, 0]],
    [2, [2, 1, 0]],
  ]);
  // A perfect Condorcet cycle A>B>C>A, no Condorcet winner.
  const cycle = ranksOf([
    [1, [0, 1, 2]],
    [1, [1, 2, 0]],
    [1, [2, 0, 1]],
  ]);

  it('smithSet is the singleton {Condorcet winner} when one exists', () => {
    expect(smithSet(cw, 3)).toEqual([1]);
  });

  it('smithSet is the whole cycle when there is no Condorcet winner', () => {
    expect(smithSet(cycle, 3)).toEqual([0, 1, 2]);
  });

  it('Condorcet-consistent extras elect the Condorcet winner', () => {
    for (const rule of [
      'black',
      'smith_irv',
      'split_cycle',
      'kemeny',
      'benham',
      'river',
      'raynaud',
    ] as Rule[])
      expect(ruleWinnerFromRanks(cw, 3, rule)).toBe(1);
  });

  it('maximin elects the least-bad option for the unhappiest voter (Rawlsian)', () => {
    // A and B are each loved by a bloc but rated 0 by the other; C is everyone's
    // decent second choice. C has the highest minimum rating → maximin winner.
    const scores = [
      [1, 0, 0.6],
      [1, 0, 0.6],
      [1, 0, 0.6],
      [0, 1, 0.6],
      [0, 1, 0.6],
    ];
    const ranks = scores.map((s) => [0, 1, 2].sort((a, b) => s[b] - s[a]));
    expect(ruleWinnerFromRanks(ranks, 3, 'maximin', scores)).toBe(2);
    // Score voting (utilitarian sum) instead rewards a loved-by-many candidate.
    expect(ruleWinnerFromRanks(ranks, 3, 'score', scores)).not.toBe(2);
  });

  it('Nash punishes zero ratings (proportional welfare, between sum and min)', () => {
    // A: sum-leader (3.0) but rated 0 by one voter → product collapses. C: 0.5 for all.
    const scores = [
      [1, 0, 0.5],
      [1, 0, 0.5],
      [0, 1, 0.5],
      [1, 1, 0.5],
    ];
    const ranks = scores.map((s) => [0, 1, 2].sort((a, b) => s[b] - s[a]));
    expect(ruleWinnerFromRanks(ranks, 3, 'score', scores)).toBe(0); // sum: A=3, B=2, C=2
    expect(ruleWinnerFromRanks(ranks, 3, 'nash', scores)).toBe(2); // product: only C avoids a 0
  });

  it('extras still return a valid candidate on a Condorcet cycle', () => {
    for (const rule of ['black', 'split_cycle'] as Rule[]) {
      const w = ruleWinnerFromRanks(cycle, 3, rule);
      expect(w).toBeGreaterThanOrEqual(0);
      expect(w).toBeLessThan(3);
    }
  });

  it('anti-plurality elects the candidate ranked last by no one', () => {
    // C (index 2) is the middle choice of everyone → never last → veto winner,
    // even though it is nobody's first choice.
    const ballots = ranksOf([
      [3, [0, 2, 1]],
      [3, [1, 2, 0]],
    ]);
    expect(ruleWinnerFromRanks(ballots, 3, 'anti_plurality')).toBe(2);
  });

  it('dowdall follows the first-preference leader (harmonic weights)', () => {
    // A leads on first prefs; 1st place (1.0) outweighs lower ranks (½, ⅓).
    const ballots = ranksOf([
      [3, [0, 1, 2]],
      [2, [1, 2, 0]],
    ]);
    expect(ruleWinnerFromRanks(ballots, 3, 'dowdall')).toBe(0);
  });
});

describe('extended method set (29 rules)', () => {
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
    for (const rule of [
      'condorcet',
      'minimax',
      'schulze',
      'nanson',
      'baldwin',
      'ranked_pairs',
    ] as Rule[]) {
      expect(ruleWinner(voters, cands, rule)).toBe(1);
    }
    expect(ruleWinner(voters, cands, 'plurality')).not.toBe(1);
  });

  it('Ranked Pairs resolves a top-cycle by locking the strongest margins', () => {
    // Cycle A>B>C>A with margins B>C=7 (strongest), A>B=5, C>A=1 (skipped).
    // Locking the first two leaves A as the source → A (index 0) wins.
    const ranks = [
      ...Array(6).fill([0, 1, 2]), // A > B > C
      ...Array(4).fill([1, 2, 0]), // B > C > A
      ...Array(3).fill([2, 0, 1]), // C > A > B
    ];
    expect(ruleWinnerFromRanks(ranks, 3, 'ranked_pairs', undefined)).toBe(0);
  });

  it('Random ballot returns the most-probable winner (modal first choice)', () => {
    const ranks = [...Array(3).fill([0, 1, 2]), [1, 0, 2]]; // A first ×3, B first ×1
    expect(ruleWinnerFromRanks(ranks, 3, 'random_ballot', undefined)).toBe(0);
  });

  it('STAR runoff can overturn the score leader', () => {
    // Score leader = B (broad), but A wins the automatic top-2 runoff 6–5.
    const ranks = [...Array(6).fill([0, 1, 2]), ...Array(5).fill([2, 1, 0])];
    const scores = [...Array(6).fill([1.0, 0.8, 0.0]), ...Array(5).fill([0.0, 0.6, 1.0])];
    expect(ruleWinnerFromRanks(ranks, 3, 'score', scores)).toBe(1); // B leads on sum
    expect(ruleWinnerFromRanks(ranks, 3, 'star', scores)).toBe(0); // A wins the runoff
  });

  it('majority judgment ranks by median grade, not mean', () => {
    // A: grades [5,5,0] median 5; B: [4,4,4] median 4 but higher mean.
    const ranks = [
      [0, 1],
      [0, 1],
      [1, 0],
    ];
    const scores = [
      [1.0, 0.7],
      [1.0, 0.7],
      [0.0, 0.7],
    ];
    expect(ruleWinnerFromRanks(ranks, 2, 'majority_judgment', scores)).toBe(0);
    expect(ruleWinnerFromRanks(ranks, 2, 'score', scores)).toBe(1); // mean favours B
  });

  it('Bucklin elects a first-round majority', () => {
    const ranks = [
      [0, 1, 2],
      [0, 1, 2],
      [0, 2, 1],
      [1, 0, 2],
      [1, 2, 0],
    ];
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

describe('random ballot (lottery) helpers', () => {
  const cands: NamedPt[] = [
    { name: 'A', x: -0.9, y: 0 },
    { name: 'B', x: 0.0, y: 0 },
    { name: 'C', x: 0.9, y: 0 },
  ];

  it('randomBallotShares are first-preference shares summing to 1', () => {
    const voters: Pt[] = [
      ...Array.from({ length: 3 }, () => ({ x: -0.95, y: 0 })), // nearest A
      ...Array.from({ length: 1 }, () => ({ x: 0.92, y: 0 })), // nearest C
    ];
    const shares = randomBallotShares(voters, cands);
    expect(shares).toEqual([0.75, 0, 0.25]);
    expect(shares.reduce((s, x) => s + x, 0)).toBeCloseTo(1, 9);
  });

  it('randomBallotProbGrid is a valid probability field in [0,1]', () => {
    const voters = sampleVoters(200, 4, 'random');
    const grid = randomBallotProbGrid(voters, cands, 8, 2);
    expect(grid.rows).toBe(8);
    expect(grid.cells).toHaveLength(64);
    expect(grid.cells.every((v) => v >= 0 && v <= 1)).toBe(true);
    // An entrant somewhere wins a non-trivial slice of first preferences.
    expect(Math.max(...grid.cells)).toBeGreaterThan(0);
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

describe('applyTurnout (electorate realism)', () => {
  const cands: NamedPt[] = [
    { name: 'L', x: -0.6, y: 0 },
    { name: 'R', x: 0.6, y: 0 },
  ];

  it('full turnout keeps everyone (rate 1)', () => {
    const voters = sampleVoters(100, 3, 'random');
    const out = applyTurnout(voters, cands, 'full', 0.8);
    expect(out.rate).toBe(1);
    expect(out.voters).toBe(voters);
  });

  it('alienation drops voters far from every candidate, more as intensity rises', () => {
    // A cloud spread across the plane; candidates only on the left/right of x.
    const voters = sampleVoters(400, 5, 'random');
    const mild = applyTurnout(voters, cands, 'alienation', 0.3).rate;
    const harsh = applyTurnout(voters, cands, 'alienation', 0.9).rate;
    expect(harsh).toBeLessThan(mild);
    expect(harsh).toBeLessThan(1);
  });

  it('indifference drops voters torn between their top two', () => {
    // Voters near the x=0 midline are equidistant from L and R → abstain.
    const voters: Pt[] = Array.from({ length: 200 }, (_, i) => ({ x: (i - 100) / 100, y: 0 }));
    const out = applyTurnout(voters, cands, 'indifference', 0.8);
    expect(out.rate).toBeLessThan(1);
    // The survivors lean clearly toward one side (|x| not tiny).
    expect(out.voters.every((v) => Math.abs(v.x) > 0.05)).toBe(true);
  });

  it('never empties the electorate (falls back to full)', () => {
    const voters = sampleVoters(50, 1, 'random');
    const out = applyTurnout(voters, cands, 'alienation', 1);
    expect(out.voters.length).toBeGreaterThanOrEqual(2);
  });

  it('differential turnout can flip the winner', () => {
    // A leads on raw plurality, but its voters are alienated extremists who
    // abstain at high intensity, handing it to the centrist M.
    const c: NamedPt[] = [
      { name: 'A', x: -0.95, y: 0 },
      { name: 'M', x: 0.1, y: 0 },
    ];
    const voters: Pt[] = [
      ...Array.from({ length: 45 }, () => ({ x: -0.99, y: 0.9 })), // far from both (alienated)
      ...Array.from({ length: 40 }, () => ({ x: 0.12, y: 0 })), // close to M
    ];
    const full = fieldWinnerName(voters, c, 'plurality');
    const filtered = applyTurnout(voters, c, 'alienation', 0.95).voters;
    const withAbstention = fieldWinnerName(filtered, c, 'plurality');
    expect(full).toBe('A');
    expect(withAbstention).toBe('M');
  });
});

describe('applyBlankVote (live blank-vote lever)', () => {
  const cands: NamedPt[] = [
    { name: 'L', x: -0.6, y: 0 },
    { name: 'R', x: 0.6, y: 0 },
  ];

  it('disabled or zero intensity is a no-op passthrough', () => {
    const voters = sampleVoters(100, 3, 'random');
    const off = applyBlankVote(voters, cands, false, 0.8);
    expect(off.blankCount).toBe(0);
    expect(off.blankShare).toBe(0);
    expect(off.expressed).toBe(voters);
    const zero = applyBlankVote(voters, cands, true, 0);
    expect(zero.blankCount).toBe(0);
    expect(zero.expressed).toBe(voters);
  });

  it('blanks out voters far from every candidate, more as intensity rises', () => {
    const voters = sampleVoters(400, 5, 'random');
    const mild = applyBlankVote(voters, cands, true, 0.3).blankShare;
    const harsh = applyBlankVote(voters, cands, true, 0.9).blankShare;
    expect(harsh).toBeGreaterThan(mild);
  });

  it('never blanks out the whole electorate (falls back to no-op)', () => {
    const voters = sampleVoters(50, 1, 'random');
    const out = applyBlankVote(voters, cands, true, 1);
    expect(out.expressed.length).toBeGreaterThanOrEqual(2);
  });

  it('a large blank bloc can flip the winner among the expressed ballots', () => {
    // R leads on raw plurality, but its voters are far from both candidates
    // (protest bloc) and go blank at high intensity, handing it to L.
    const voters: Pt[] = [
      ...Array.from({ length: 45 }, () => ({ x: 0.95, y: 0.9 })), // far from both → blank
      ...Array.from({ length: 40 }, () => ({ x: -0.55, y: 0 })), // close to L
    ];
    const full = fieldWinnerName(voters, cands, 'plurality');
    const { expressed } = applyBlankVote(voters, cands, true, 0.95);
    const withBlank = fieldWinnerName(expressed, cands, 'plurality');
    expect(full).toBe('R');
    expect(withBlank).toBe('L');
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
    const spread = (pts: Pt[]) =>
      Math.max(...pts.map((p) => p.x)) - Math.min(...pts.map((p) => p.x));
    expect(spread(sampleVoters(400, 1, 'polarized'))).toBeGreaterThan(
      spread(sampleVoters(400, 1, 'centrist'))
    );
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// The spatial helpers, asserted on VALUES rather than on shape.
//
// The tests above already covered these — but only as "returns 64 cells" and
// "every value is in [0, 1]". Mutation testing showed what that buys: 46 mutants
// survive across randomBallotProbGrid (21), applyTurnout (10), winRegionGrid (9)
// and applyBlankVote (6), because you can flip the sign of a coordinate, invert
// a comparison or change a radius and still return a correctly-shaped grid of
// in-range numbers.
//
// These fix the geometry to hand-computable answers instead.
// ─────────────────────────────────────────────────────────────────────────────
describe('spatial helpers — exact values', () => {
  // With n = 2 the cell centres are the four points (±0.5, ±0.5):
  //   x = ((c + 0.5) / n) * 2 - 1   →  c=0 → -0.5,  c=1 → +0.5
  //   y = 1 - ((r + 0.5) / n) * 2   →  r=0 → +0.5,  r=1 → -0.5   (y descends)
  // so row-major order is  (-0.5,+0.5) (+0.5,+0.5) (-0.5,-0.5) (+0.5,-0.5).
  const CELL_CENTRES: Pt[] = [
    { x: -0.5, y: 0.5 },
    { x: 0.5, y: 0.5 },
    { x: -0.5, y: -0.5 },
    { x: 0.5, y: -0.5 },
  ];

  it('randomBallotProbGrid places cells on the exact grid centres', () => {
    // One voter sitting on cell 0's centre, one candidate on cell 1's centre.
    // The voter is 1.0 from the candidate, so a hypothetical entrant is its
    // nearest option in every cell except the far diagonal (distance √2).
    const voters: Pt[] = [CELL_CENTRES[0]];
    const cands: NamedPt[] = [{ name: 'A', x: 0.5, y: 0.5 }];

    const grid = randomBallotProbGrid(voters, cands, 2, 2);

    // Flipping either axis, or transposing row-major to column-major, permutes
    // this vector — which is the point of asserting it rather than its length.
    expect(grid.cells).toEqual([1, 1, 1, 0]);
    expect(grid.rows).toBe(2);
    expect(grid.n).toBe(2);
  });

  it('randomBallotProbGrid ties go to the entrant (strictly-nearer wins)', () => {
    // Cell 1's centre IS the candidate's position: the entrant ties, and the
    // rule is dist(v, cand) < dh — strict, so a tie leaves H nearest.
    const voters: Pt[] = [CELL_CENTRES[0]];
    const cands: NamedPt[] = [{ name: 'A', x: 0.5, y: 0.5 }];

    expect(randomBallotProbGrid(voters, cands, 2, 2).cells[1]).toBe(1);
  });

  it('randomBallotProbGrid divides by the electorate, not the cell count', () => {
    // Three voters on cell 0's centre, one far away and firmly the candidate's.
    // Cell 0 therefore wins exactly 3 of 4 first preferences.
    const voters: Pt[] = [CELL_CENTRES[0], CELL_CENTRES[0], CELL_CENTRES[0], { x: 0.99, y: -0.99 }];
    const cands: NamedPt[] = [{ name: 'A', x: 0.95, y: -0.95 }];

    expect(randomBallotProbGrid(voters, cands, 2, 2).cells[0]).toBeCloseTo(0.75, 12);
  });

  it('a 1-D grid is a single row, not an n x n square', () => {
    const voters = sampleVoters(20, 3, 'random', 1);
    const cands: NamedPt[] = [{ name: 'A', x: 0.5, y: 0 }];

    const prob = randomBallotProbGrid(voters, cands, 6, 1);
    expect(prob.rows).toBe(1);
    expect(prob.cells).toHaveLength(6);

    const win = winRegionGrid(voters, cands, 'plurality', 6, 1);
    expect(win.rows).toBe(1);
    expect(win.cells).toHaveLength(6);
  });

  it('the win region and the probability field share one cell geometry', () => {
    // Head-to-head against a single incumbent, an entrant wins a cell under
    // plurality exactly when it holds more than half the first preferences
    // there — which is what randomBallotProbGrid reports for the same cell.
    //
    // Asserting the two agree cell-for-cell pins BOTH grids to the same
    // coordinate mapping. Shifting a half-cell in one of them (the mutation
    // that a "the entrant wins everywhere" assertion cannot see, because it
    // stays true wherever the cells are) desynchronises the pair.
    const voters = sampleVoters(101, 7, 'random'); // odd: no 50/50 cell
    const cands: NamedPt[] = [{ name: 'A', x: 0.4, y: -0.3 }];

    const win = winRegionGrid(voters, cands, 'plurality', 6, 2);
    const prob = randomBallotProbGrid(voters, cands, 6, 2);

    expect(win.cells).toHaveLength(prob.cells.length);
    const entrant = cands.length;
    win.cells.forEach((w, i) => {
      expect(w === entrant).toBe(prob.cells[i] > 0.5);
    });
    // …and the entrant genuinely wins somewhere and loses somewhere, so the
    // invariant above is not satisfied by a constant grid.
    expect(win.cells.some((w) => w === entrant)).toBe(true);
    expect(win.cells.some((w) => w !== entrant)).toBe(true);
  });

  it('randomBallotShares break a distance tie toward the first candidate', () => {
    // The voter is exactly equidistant from A and B. The scan keeps the best
    // seen so far on d < bd, so the earlier index wins.
    const voters: Pt[] = [{ x: 0, y: 0 }];
    const cands: NamedPt[] = [
      { name: 'A', x: -1, y: 0 },
      { name: 'B', x: 1, y: 0 },
    ];

    expect(randomBallotShares(voters, cands)).toEqual([1, 0]);
  });
});

describe('turnout and blank vote — exact thresholds', () => {
  const oneCandidate: NamedPt[] = [{ name: 'A', x: 0, y: 0 }];

  // alienation radius = (1 - k) * 1.5 + 0.2, so k = 1 gives exactly 0.2.
  const nearAndFar: Pt[] = [
    { x: 0.1, y: 0 },
    { x: 0.15, y: 0 },
    { x: 0.9, y: 0 },
    { x: 0.9, y: 0 },
  ];

  it('alienation abstains beyond the radius the intensity sets', () => {
    const out = applyTurnout(nearAndFar, oneCandidate, 'alienation', 1);

    expect(out.voters).toHaveLength(2);
    expect(out.rate).toBe(0.5);
    expect(out.voters.every((v) => v.x <= 0.2)).toBe(true);
  });

  it('alienation keeps a voter sitting exactly on the radius', () => {
    // ds[0] <= radius is inclusive; at k = 1 the radius is 0.2 and this voter
    // is at 0.2. Two more inside, so the "never empty the electorate" floor
    // does not mask the result.
    const onTheLine: Pt[] = [
      { x: 0.2, y: 0 },
      { x: 0.05, y: 0 },
      { x: 0.05, y: 0 },
      { x: 0.9, y: 0 },
    ];

    expect(applyTurnout(onTheLine, oneCandidate, 'alienation', 1).voters).toHaveLength(3);
  });

  it('indifference abstains when the top two are too close together', () => {
    // margin = k * 0.4, so 0.2 at k = 0.5. A voter votes only when the gap
    // between its two nearest candidates EXCEEDS the margin.
    const cands: NamedPt[] = [
      { name: 'L', x: -1, y: 0 },
      { name: 'R', x: 1, y: 0 },
    ];
    const voters: Pt[] = [
      { x: -0.9, y: 0 }, // gap 1.8  -> votes
      { x: 0.9, y: 0 }, //  gap 1.8  -> votes
      { x: 0, y: 0 }, //    gap 0    -> abstains, perfectly torn
      { x: 0.05, y: 0 }, // gap 0.1  -> abstains, under the margin
    ];

    const out = applyTurnout(voters, cands, 'indifference', 0.5);

    expect(out.voters).toHaveLength(2);
    expect(out.rate).toBe(0.5);

    // NOTE: `ds[1] - ds[0] > margin` versus `>= margin` is an EQUIVALENT mutant
    // here, and deliberately left alive. Separating them needs a voter whose gap
    // equals the margin exactly, and the margin is k * 0.4 — a value with no
    // exact binary representation. A voter placed to sit "on the line" lands at
    // 0.20000000000000007 against a margin of 0.2 and votes either way. The
    // boundary is unreachable with real inputs, so a test that appeared to cover
    // it would only be testing floating-point noise.
  });

  it('turnout never empties the electorate', () => {
    // Only one voter survives the radius, so the model hands the full
    // electorate back rather than running an election on a single ballot.
    const mostlyFar: Pt[] = [
      { x: 0.1, y: 0 },
      { x: 0.9, y: 0 },
      { x: 0.9, y: 0 },
      { x: 0.9, y: 0 },
    ];

    const out = applyTurnout(mostlyFar, oneCandidate, 'alienation', 1);

    expect(out.voters).toHaveLength(4);
    expect(out.rate).toBe(1);
  });

  it('a full-turnout model leaves the electorate untouched', () => {
    const out = applyTurnout(nearAndFar, oneCandidate, 'full', 1);

    expect(out.voters).toBe(nearAndFar);
    expect(out.rate).toBe(1);
  });

  it('zero intensity leaves the electorate untouched', () => {
    expect(applyTurnout(nearAndFar, oneCandidate, 'alienation', 0).rate).toBe(1);
  });

  it('blank vote splits on the same radius and reports its share', () => {
    const out = applyBlankVote(nearAndFar, oneCandidate, true, 1);

    expect(out.expressed).toHaveLength(2);
    expect(out.blankCount).toBe(2);
    expect(out.blankShare).toBe(0.5);
  });

  it('blank vote never blanks out the whole electorate', () => {
    const mostlyFar: Pt[] = [
      { x: 0.1, y: 0 },
      { x: 0.9, y: 0 },
      { x: 0.9, y: 0 },
      { x: 0.9, y: 0 },
    ];

    const out = applyBlankVote(mostlyFar, oneCandidate, true, 1);

    expect(out.expressed).toHaveLength(4);
    expect(out.blankCount).toBe(0);
    expect(out.blankShare).toBe(0);
  });

  it('a disabled blank vote expresses everyone', () => {
    const out = applyBlankVote(nearAndFar, oneCandidate, false, 1);

    expect(out.expressed).toBe(nearAndFar);
    expect(out.blankCount).toBe(0);
  });
});

// ────────────────────────────────────────────────────────────────────────────
// The branches no test reached.
//
// Stryker reported nine mutants with NO covering test at all, in a file whose
// line coverage sits above 85%. Every one of them guards a degenerate or
// defensive case: the electorate is empty, the field is empty, or an
// elimination round wipes out every remaining candidate at once.
//
// These are the cases a real user hits by dragging the last candidate off the
// map, or by loading a saved URL whose rule no longer exists. Leaving them
// unasserted means the app's behaviour there is whatever the code happens to do.
// ─────────────────────────────────────────────────────────────────────────────
describe('degenerate cases — no winner, empty field, unknown rule', () => {
  // A perfect 3-way Condorcet cycle: every candidate is first once, last once,
  // and beaten by exactly one other. Nothing distinguishes them, so an
  // elimination round condemns all three at the same time.
  const CYCLE = ranksOf([
    [1, [0, 1, 2]], // A > B > C
    [1, [1, 2, 0]], // B > C > A
    [1, [2, 0, 1]], // C > A > B
  ]);

  // The four rules that eliminate iteratively all share the same guard:
  //   if (doomed.length >= remaining) return -1;   // every survivor tied
  // Without it they would eliminate the whole field and then index into an
  // empty set. -1 is the file's "no winner" sentinel.
  it.each(['irv', 'coombs', 'smith_irv', 'benham'] as const)(
    '%s reports no winner when a round would eliminate every survivor',
    (rule) => {
      expect(ruleWinnerFromRanks(CYCLE, 3, rule)).toBe(-1);
    }
  );

  // NOTE: `doomed.length >= remaining` versus `> remaining` is an EQUIVALENT
  // mutant. doomed is a subset of the alive set, so `>` is never true; without
  // the early return the round eliminates everyone, remaining falls to 0, the
  // while loop exits and findIndex finds no survivor — returning the same -1.
  // The guard is a short-circuit and a piece of documentation, not a behaviour.
  // No test can separate the two, and one that appeared to would be asserting
  // something else.

  it('a cycle has no Condorcet winner, but the condorcet RULE still elects one', () => {
    // The premise of the four cases above: none of them can short-circuit to a
    // Condorcet winner, because the cycle has none.
    expect(condorcetWinnerIdx(CYCLE, 3)).toBe(-1);

    // The rule the UI labels "condorcet" is Copeland — pairwise wins minus
    // losses, Borda as tie-break — so it always resolves a cycle rather than
    // reporting no winner. Worth pinning: the helper and the rule share a name
    // and answer different questions.
    expect(ruleWinnerFromRanks(CYCLE, 3, 'condorcet')).toBeGreaterThanOrEqual(0);
  });

  it('an empty field has no winner', () => {
    expect(ruleWinnerFromRanks([], 0, 'plurality')).toBe(-1);
    expect(ruleWinnerFromRanks(CYCLE, 0, 'plurality')).toBe(-1);
  });

  it('an empty ballot box has no winner', () => {
    expect(ruleWinnerFromRanks([], 3, 'plurality')).toBe(-1);
  });

  it('a spatial election with no candidates has no winner', () => {
    const voters: Pt[] = [{ x: 0, y: 0 }];
    expect(ruleWinner(voters, [], 'plurality')).toBe(-1);
  });

  it('a spatial election with no voters has no winner', () => {
    const cands: NamedPt[] = [{ name: 'A', x: 0, y: 0 }];
    expect(ruleWinner([], cands, 'plurality')).toBe(-1);
  });

  // The guards above answer "is this degenerate?". Asserting only the
  // degenerate side lets the threshold slip by one and still return -1 for an
  // empty field — because an empty field returns -1 further down anyway. These
  // pin the SMALLEST valid election, which a slipped guard would wrongly call
  // degenerate.
  it('the smallest valid election still elects its only candidate', () => {
    const oneBallot = ranksOf([[1, [0]]]);
    expect(ruleWinnerFromRanks(oneBallot, 1, 'plurality')).toBe(0);

    const oneVoter: Pt[] = [{ x: 0, y: 0 }];
    const oneCand: NamedPt[] = [{ name: 'A', x: 0.2, y: 0 }];
    expect(ruleWinner(oneVoter, oneCand, 'plurality')).toBe(0);
  });

  it('an unknown rule id falls back to plurality rather than crashing', () => {
    // The dispatch switch covers every member of the Rule union, so this branch
    // is unreachable through the type system — but rule ids also arrive from
    // saved URLs and stored state, where nothing checks them. The fallback is a
    // runtime guard, and this pins what it does instead of leaving it to chance.
    const clear = ranksOf([
      [3, [0, 1, 2]],
      [1, [1, 0, 2]],
      [1, [2, 1, 0]],
    ]);

    const fallback = ruleWinnerFromRanks(clear, 3, 'not_a_real_rule' as Rule);

    expect(fallback).toBe(ruleWinnerFromRanks(clear, 3, 'plurality'));
    expect(fallback).toBe(0); // A, on 3 of 5 first preferences
  });
});
