import { describe, it, expect } from 'vitest';
import {
  sincerityProbe,
  sincerityScan,
  manipulationField,
  strategicVote,
} from './playgroundSincerity';
import type { NamedPt, Pt } from './playgroundVoting';

// A textbook spoiler on a 1-D line: A (your favourite, left), B (centre), C (right).
const CANDS: NamedPt[] = [
  { name: 'A', x: -0.8, y: 0 },
  { name: 'B', x: 0.0, y: 0 },
  { name: 'C', x: 0.7, y: 0 },
];
const YOU: Pt = { x: -0.9, y: 0 }; // sincere order A > B > C
// 40 right voters elect C under plurality; 35 centre voters back B.
const OTHERS: Pt[] = [
  ...Array.from({ length: 40 }, () => ({ x: 0.75, y: 0 })),
  ...Array.from({ length: 35 }, () => ({ x: 0.05, y: 0 })),
];
const BLOC_SHARE = 10 / 75; // → a bloc of ~10 like-minded voters

describe('sincerityProbe', () => {
  it('returns one verdict per leader rule with your sincere ranking', () => {
    const r = sincerityProbe(YOU, BLOC_SHARE, OTHERS, CANDS);
    expect(r.ranking).toEqual(['A', 'B', 'C']);
    expect(r.blocSize).toBe(10);
    expect(r.verdicts).toHaveLength(25);
  });

  it('is deterministic', () => {
    expect(sincerityProbe(YOU, BLOC_SHARE, OTHERS, CANDS)).toEqual(
      sincerityProbe(YOU, BLOC_SHARE, OTHERS, CANDS)
    );
  });

  it('random ballot is never tempting (strategyproof, Gibbard 1977)', () => {
    const v = sincerityProbe(YOU, BLOC_SHARE, OTHERS, CANDS).verdicts.find(
      (x) => x.rule === 'random_ballot'
    )!;
    expect(v.sincereIsBest).toBe(true);
    expect(v.temptation).toBeNull();
    expect(v.gain).toBe(0);
  });

  it('plurality tempts the "vote utile" (compromise to B flips C→B)', () => {
    const r = sincerityProbe(YOU, BLOC_SHARE, OTHERS, CANDS);
    const plur = r.verdicts.find((v) => v.rule === 'plurality')!;
    expect(plur.sincereWinner).toBe('C'); // your favourite A is a no-hoper
    expect(plur.sincereIsBest).toBe(false);
    expect(plur.temptation).toEqual({ type: 'compromise', voteFor: 'B', newWinner: 'B' });
    // The lie's winner (B) is genuinely closer to you than the sincere winner (C).
    expect(plur.gain).toBeGreaterThan(0);
  });

  it('a Condorcet method rewards conviction (sincere is the best response)', () => {
    const r = sincerityProbe(YOU, BLOC_SHARE, OTHERS, CANDS);
    const cond = r.verdicts.find((v) => v.rule === 'condorcet')!;
    expect(cond.sincereWinner).toBe('B'); // B is the Condorcet winner
    expect(cond.sincereIsBest).toBe(true);
    expect(cond.temptation).toBeNull();
  });

  it('methods split into conviction-safe vs strategy-tempting (the project thesis)', () => {
    const r = sincerityProbe(YOU, BLOC_SHARE, OTHERS, CANDS);
    const safe = r.verdicts.filter((v) => v.sincereIsBest).length;
    const tempting = r.verdicts.length - safe;
    expect(safe).toBeGreaterThan(0);
    expect(tempting).toBeGreaterThan(0); // the methods genuinely differ
  });

  it('sincerityScan ranks methods by how often they tempt voters (best first)', () => {
    // A realistic 3-cluster electorate so sampled archetypes include left voters
    // (spoiler victims under plurality), not only centre/right ones.
    const scanOthers: Pt[] = [
      ...Array.from({ length: 20 }, () => ({ x: -0.85, y: 0 })),
      ...Array.from({ length: 35 }, () => ({ x: 0.05, y: 0 })),
      ...Array.from({ length: 40 }, () => ({ x: 0.75, y: 0 })),
    ];
    const scan = sincerityScan(scanOthers, CANDS, BLOC_SHARE, 30);
    expect(scan.sampled).toBeGreaterThan(0);
    expect(scan.rows).toHaveLength(25);
    // Every rate is a probability.
    expect(scan.rows.every((r) => r.temptRate >= 0 && r.temptRate <= 1)).toBe(true);
    // Sorted ascending (lowest temptation = most conviction-friendly first).
    const rates = scan.rows.map((r) => r.temptRate);
    expect([...rates].sort((a, b) => a - b)).toEqual(rates);
    // The scan detects strategic temptation, and plurality is among the tempted.
    expect(rates.some((r) => r > 0)).toBe(true);
    const plur = scan.rows.find((r) => r.rule === 'plurality')!;
    expect(plur.temptRate).toBeGreaterThan(0);
  });

  it('no strategic dilemma with fewer than three candidates', () => {
    const two: NamedPt[] = [
      { name: 'A', x: -0.5, y: 0 },
      { name: 'B', x: 0.5, y: 0 },
    ];
    const r = sincerityProbe(YOU, BLOC_SHARE, OTHERS, two);
    expect(r.verdicts.every((v) => v.sincereIsBest)).toBe(true);
  });
});

describe('manipulationField (per-voter lens)', () => {
  // A spoiler electorate: left bloc (favours A) is squeezed; B is the centre.
  const cands: NamedPt[] = [
    { name: 'A', x: -0.8, y: 0 },
    { name: 'B', x: 0.0, y: 0 },
    { name: 'C', x: 0.75, y: 0 },
  ];
  // Small A bloc (can't win even with its conviction bloc) → spoiler pressure to
  // compromise on B; B beats C once the left consolidates.
  const voters: Pt[] = [
    ...Array.from({ length: 15 }, () => ({ x: -0.85, y: 0 })), // A-first (spoiler victims)
    ...Array.from({ length: 25 }, () => ({ x: 0.05, y: 0 })), // B-first
    ...Array.from({ length: 35 }, () => ({ x: 0.78, y: 0 })), // C-first (plurality winner)
  ];

  it('returns one verdict per voter and stays deterministic', () => {
    const a = manipulationField(voters, cands, 'plurality', 0.15);
    const b = manipulationField(voters, cands, 'plurality', 0.15);
    expect(a).toHaveLength(voters.length);
    expect(a).toEqual(b);
    expect(a.every((k) => k === null || k === 'compromise' || k === 'burying')).toBe(true);
  });

  it('plurality tempts the squeezed left bloc to compromise (vote utile)', () => {
    const field = manipulationField(voters, cands, 'plurality', 0.2);
    // The A-first voters (whose favourite cannot win) are pushed to compromise.
    expect(field.some((k) => k === 'compromise')).toBe(true);
  });

  it('random ballot tempts no one (strategyproof, Gibbard 1977)', () => {
    const field = manipulationField(voters, cands, 'random_ballot', 0.2);
    expect(field.every((k) => k === null)).toBe(true);
  });

  it('no temptation with fewer than three candidates', () => {
    const two: NamedPt[] = [
      { name: 'A', x: -0.5, y: 0 },
      { name: 'B', x: 0.5, y: 0 },
    ];
    const field = manipulationField(voters, two, 'plurality', 0.2);
    expect(field.every((k) => k === null)).toBe(true);
  });
});

describe('strategicVote (behaviour drives the winner)', () => {
  // Same spoiler electorate: sincere plurality elects C; the squeezed left
  // compromises on B, flipping the winner.
  const cands: NamedPt[] = [
    { name: 'A', x: -0.8, y: 0 },
    { name: 'B', x: 0.0, y: 0 },
    { name: 'C', x: 0.75, y: 0 },
  ];
  const voters: Pt[] = [
    ...Array.from({ length: 15 }, () => ({ x: -0.85, y: 0 })),
    ...Array.from({ length: 25 }, () => ({ x: 0.05, y: 0 })),
    ...Array.from({ length: 35 }, () => ({ x: 0.78, y: 0 })),
  ];

  it('sincere behaviour leaves the winner unchanged', () => {
    const out = strategicVote(voters, cands, 'plurality', 'sincere')!;
    expect(out.strategicWinner).toBe(out.sincereWinner);
    expect(out.defectRate).toBe(0);
  });

  it('strategic behaviour flips plurality from C to B (vote utile)', () => {
    const out = strategicVote(voters, cands, 'plurality', 'strategic')!;
    expect(cands[out.sincereWinner].name).toBe('C');
    expect(cands[out.strategicWinner].name).toBe('B');
    expect(out.defectRate).toBeGreaterThan(0);
  });

  it('is deterministic and defectors align with the sample', () => {
    const a = strategicVote(voters, cands, 'plurality', 'strategic')!;
    const b = strategicVote(voters, cands, 'plurality', 'strategic')!;
    expect(a).toEqual(b);
    expect(a.defectors).toHaveLength(a.sampled);
  });

  it('random ballot is strategyproof — no defection, no flip', () => {
    const out = strategicVote(voters, cands, 'random_ballot', 'strategic')!;
    expect(out.strategicWinner).toBe(out.sincereWinner);
    expect(out.defectRate).toBe(0);
  });

  it('mixed defects fewer voters than fully strategic', () => {
    const mixed = strategicVote(voters, cands, 'plurality', 'mixed')!;
    const strat = strategicVote(voters, cands, 'plurality', 'strategic')!;
    expect(mixed.defectRate).toBeLessThanOrEqual(strat.defectRate);
    expect(mixed.defectRate).toBeGreaterThan(0);
  });

  it('the compromise tactic reproduces the vote-utile flip C→B', () => {
    const out = strategicVote(voters, cands, 'plurality', 'strategic', { tactic: 'compromise' })!;
    expect(cands[out.strategicWinner].name).toBe('B');
    expect(out.defectRate).toBeGreaterThan(0);
  });

  it('a smaller coalition share tempts no more voters than a larger one', () => {
    const small = strategicVote(voters, cands, 'plurality', 'strategic', { blocShare: 0.05 })!;
    const large = strategicVote(voters, cands, 'plurality', 'strategic', { blocShare: 0.5 })!;
    expect(small.defectRate).toBeLessThanOrEqual(large.defectRate);
  });
});
