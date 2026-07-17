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

// Same honesty gate for Alaska. Source: Graham-Squire & McCune, arXiv:2303.00108,
// Table 4 (published ballot-type breakdown of the state's cast vote record). The
// numbers below are the paper's OWN reported aggregates — our tabulator must
// reproduce them from the shipped ballots, or the "real election" claim is fiction.
// Candidate order in the fixture: 0 Begich · 1 Palin · 2 Peltola.
const ak = (fixture as { elections: RealElection[] }).elections.find(
  (e) => e.id === 'ak-2022-special'
)!;

describe('Alaska 2022 special backtest — matches the published record', () => {
  it('loaded all 188 582 ballots', () => {
    expect(ak.voters).toBe(188582);
  });

  it('first preferences match the certified round-one count', () => {
    // Peltola 75 799 · Palin 58 973 · Begich 53 810 — Begich is eliminated first
    // precisely BECAUSE he is third here. That is the whole story.
    const first = [0, 0, 0];
    for (const b of ak.ballots) first[b.groups[0][0]] += b.n;
    expect(first).toEqual([53810, 58973, 75799]);
  });

  it('pairwise matrix matches the paper exactly — Begich beats BOTH rivals', () => {
    const p = pairwiseMatrix(ak);
    expect([p[0][1], p[1][0]]).toEqual([101217, 63618]); // Begich > Palin
    expect([p[0][2], p[2][0]]).toEqual([87859, 79451]); // Begich > Peltola
    expect([p[2][1], p[1][2]]).toEqual([91266, 86026]); // Peltola > Palin
  });

  it('the Condorcet failure: IRV elects Peltola, but Begich is the Condorcet winner', () => {
    const bt = backtest(ak);
    const winner = (m: string) => bt.results.find((r) => r.method === m)!.winner;
    // Peltola led first preferences, so plurality crowns her too — the plan's
    // "plurality → Palin" was simply wrong; Palin never leads on any method here.
    expect(winner('plurality')).toBe('Peltola');
    expect(winner('two_round')).toBe('Peltola');
    expect(winner('irv')).toBe('Peltola');
    expect(winner('condorcet')).toBe('Begich'); // beats Palin AND Peltola head-to-head
    expect(winner('minimax')).toBe('Begich');
    expect(bt.distinctWinners).toBe(2);
  });

  it('IRV final round is Peltola 91 266 vs Palin 86 026', () => {
    const irv = backtest(ak).results.find((r) => r.method === 'irv')!;
    expect(irv.detail).toContain('91266');
    expect(irv.detail).toContain('86026');
  });
});
