import { describe, it, expect } from 'vitest';
import { voteFrames, frameWinner, RANKS, SCORES, FOOD_COUNT, ELECTORATE } from './discoverVoteAnim';
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
