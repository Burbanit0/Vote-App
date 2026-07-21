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

  it('every duel splits the whole electorate between the two options', () => {
    for (const f of voteFrames('condorcet'))
      if (f.kind === 'duel')
        for (const d of f.duels) expect(d.leftVotes + d.rightVotes).toBe(ELECTORATE);
  });
});
