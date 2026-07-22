import { describe, it, expect } from 'vitest';
import {
  voteFrames,
  frameWinner,
  approvalCountsForK,
  RANKS,
  SCORES,
  FOOD_COUNT,
  ELECTORATE,
} from './discoverVoteAnim';
import { ruleWinnerFromRanks, type Rule } from './playgroundVoting';

const RULES: Rule[] = ['plurality', 'two_round', 'approval', 'condorcet'];

describe('discoverVoteAnim', () => {
  it('the animation ends on the same winner the real engine elects', () => {
    for (const r of RULES) {
      const engine = ruleWinnerFromRanks(
        RANKS,
        FOOD_COUNT,
        r,
        r === 'approval' ? SCORES : undefined
      );
      expect(frameWinner(r), r).toBe(engine);
    }
  });

  it('the approval threshold slides the winner: favourite-only = plurality (Pizza), broader = Thaï', () => {
    const c1 = approvalCountsForK(1); // approve only your first choice
    expect(c1.indexOf(Math.max(...c1))).toBe(0); // Pizza — identical to plurality
    const c2 = approvalCountsForK(2); // approve your two favourites
    expect(c2.indexOf(Math.max(...c2))).toBe(2); // Thaï — the compromise
    expect(c2[2]).toBe(ELECTORATE); // Thaï is in everyone's top two → all 12
    const c3 = approvalCountsForK(3); // approve everyone → no discrimination
    expect(new Set(c3).size).toBe(1); // a dead tie
  });

  it('the three methods do not all crown the same option (the whole point)', () => {
    const winners = new Set(RULES.map(frameWinner));
    expect(winners.size).toBeGreaterThanOrEqual(3);
  });

  it('tally frames never exceed the electorate and stay non-negative', () => {
    for (const r of RULES)
      for (const f of voteFrames(r))
        if (f.kind === 'tally')
          for (const b of f.bars) {
            expect(b.value).toBeGreaterThanOrEqual(0);
            expect(b.value).toBeLessThanOrEqual(ELECTORATE);
          }
  });

  it('the runoff round-2 pile is own + transferred, tagged with the eliminated option', () => {
    const frames = voteFrames('two_round');
    const round1 = frames[0];
    const round2 = frames[1];
    if (round1.kind !== 'tally' || round2.kind !== 'tally') throw new Error('expected tallies');
    for (const bar of round2.bars) {
      const own = round1.bars.find((b) => b.food === bar.food)!.value;
      if (bar.received) {
        // A finalist keeps its own first-choicers; extras are transferred ballots.
        expect(bar.received).toBe(bar.value - own); // exactly the redistributed pile
        expect(bar.from).not.toBeUndefined(); // and it knows where they came from
      }
    }
    // Exactly one pile receives ballots here (Thaï → Sushi), and it names Thaï.
    const receivers = round2.bars.filter((b) => b.received);
    expect(receivers).toHaveLength(1);
    expect(receivers[0].from).toBe(2); // Thaï
  });

  it('every duel splits the whole electorate between the two options', () => {
    for (const f of voteFrames('condorcet'))
      if (f.kind === 'duel')
        for (const d of f.duels) expect(d.leftVotes + d.rightVotes).toBe(ELECTORATE);
  });
});
