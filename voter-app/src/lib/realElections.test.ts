import { describe, it, expect } from 'vitest';
import { backtest, pairwiseMatrix, type RealElection } from './realElections';
import fixture from './__fixtures__/realElections.json';

// Honesty gate: the backtest must reproduce the DOCUMENTED 2009 Burlington
// results. If the parser or the tabulator drifts, these published numbers stop
// matching — so the "real election" claim can't quietly become fiction.
// Candidate order in the fixture: 0 Kiss · 1 Montroll · 2 Simpson · 3 Smith ·
// 4 Wright · 5 Write-In.
const btv = (fixture as { elections: RealElection[] }).elections.find((e) => e.id === 'btv-2009')!;

describe('Burlington 2009 backtest — matches the published record', () => {
  it('loaded all 8980 ballots', () => {
    expect(btv.voters).toBe(8980);
  });

  // Head-to-heads from the PrefLib .toi we actually ship. These sit within a
  // handful of ballots of the widely-cited Wikipedia figures (4064/4313/…) — the
  // official report cleaned a few overvoted ballots differently — but the source
  // we tabulate must reproduce its own numbers exactly, and every winner is the
  // same under either source.
  it('pairwise matrix matches the PrefLib source exactly', () => {
    const p = pairwiseMatrix(btv);
    expect([p[1][0], p[0][1]]).toEqual([4067, 3477]); // Montroll > Kiss
    expect([p[0][4], p[4][0]]).toEqual([4314, 4064]); // Kiss > Wright
    expect([p[1][4], p[4][1]]).toEqual([4597, 3668]); // Montroll > Wright
    expect([p[1][3], p[3][1]]).toEqual([4573, 2998]); // Montroll > Smith
  });

  it('the method changes the winner: Wright / Kiss / Montroll', () => {
    const bt = backtest(btv);
    const winner = (m: string) => bt.results.find((r) => r.method === m)!.winner;
    expect(winner('plurality')).toBe('Wright'); // first preferences
    expect(winner('two_round')).toBe('Kiss'); // top-2 runoff
    expect(winner('irv')).toBe('Kiss'); // transfers
    expect(winner('condorcet')).toBe('Montroll'); // beats every rival head-to-head
    expect(winner('minimax')).toBe('Montroll');
    expect(bt.distinctWinners).toBe(3);
  });

  it('IRV final round is Kiss 4314 vs Wright 4064 (PrefLib source)', () => {
    const irv = backtest(btv).results.find((r) => r.method === 'irv')!;
    expect(irv.detail).toContain('4314');
    expect(irv.detail).toContain('4064');
  });
});
