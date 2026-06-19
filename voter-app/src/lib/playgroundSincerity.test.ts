import { describe, it, expect } from 'vitest';
import { sincerityProbe, sincerityScan } from './playgroundSincerity';
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
    expect(r.verdicts).toHaveLength(17);
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
    expect(scan.rows).toHaveLength(17);
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
