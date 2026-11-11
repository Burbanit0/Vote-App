import { describe, expect, it } from 'vitest';
import { ruleWinner } from '../playgroundVoting';
import { LEADER_RULES, hasFixedWinner } from '../scorecard';
import { ENGINE_RULE, METHOD_WINNERS, winsByCandidate } from './methods';
import { CANDIDATES, RULES, TALLY, VOTERS } from './scenario';

describe('the homepage’s winners under every method', () => {
  it('lists every method with a fixed winner, in the instrument’s order', () => {
    expect(METHOD_WINNERS.map((m) => m.rule)).toEqual(LEADER_RULES.filter(hasFixedWinner));
  });

  it('agrees with the voting engine on every method but approval', () => {
    METHOD_WINNERS.filter((m) => m.rule !== 'approval').forEach((m) =>
      expect([m.rule, ruleWinner(VOTERS, CANDIDATES, m.rule)]).toEqual([m.rule, m.winner])
    );
  });

  it('agrees with the hero and the count on its three rules', () => {
    RULES.forEach((r) => {
      const m = METHOD_WINNERS.find((x) => x.rule === ENGINE_RULE[r])!;
      expect(m.winner).toBe(TALLY[r].winner);
    });
  });

  it('counts the methods each candidate wins', () => {
    expect(winsByCandidate()).toEqual([2, 24, 2]);
  });
});
