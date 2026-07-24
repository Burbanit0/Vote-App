import { describe, it, expect } from 'vitest';
import {
  BALLOT_LANGUAGES,
  RULES_FOR,
  ballotFrom,
  gradesOf,
  pointsOf,
  orderOf,
  electorateBallots,
} from './ballotLanguages';
import { CANDIDATES, ELECTORATE, DEFAULT_YOU, winnersFor, yourRankOf } from './votePlay';
import { ruleWinnerFromRanks, computeRanks, sampleVoters, computeScores } from './playgroundVoting';

const M = CANDIDATES.length;

describe('ballotLanguages — one opinion, five papers', () => {
  it('every language preserves the voter’s order', () => {
    const aff = [0.72, 0.05, 0.95, 0.4];
    const want = orderOf(aff); // Carla › Alice › Diane › Bruno
    for (const lang of BALLOT_LANGUAGES) {
      expect(ballotFrom(aff, lang).rank, lang).toEqual(want);
    }
  });

  it('a ranked ballot does not invent an order the engine would not derive', () => {
    // The translation must agree with the engine's own ranking of the same voters.
    const voters = sampleVoters(20, 5, 'random', 2);
    const aff = computeScores(voters, CANDIDATES);
    const engineRanks = computeRanks(voters, CANDIDATES);
    aff.forEach((a, i) => expect(ballotFrom(a, 'rank').rank).toEqual(engineRanks[i]));
  });

  it('the richer the paper, the more methods it unlocks', () => {
    expect(RULES_FOR.one).toHaveLength(1); // a single name unlocks plurality, nothing else
    expect(RULES_FOR.rank.length).toBeGreaterThan(RULES_FOR.one.length);
    // No language claims a rule it cannot feed.
    expect(RULES_FOR.one).not.toContain('condorcet');
    expect(RULES_FOR.one).not.toContain('two_round'); // a runoff needs a SECOND ballot
    expect(RULES_FOR.rank).toContain('condorcet');
  });

  it('approval ticks exactly k candidates, best first', () => {
    const aff = [0.72, 0.05, 0.95, 0.4];
    for (const k of [1, 2, 3, 4]) {
      const s = ballotFrom(aff, 'approve', { approveK: k }).score!;
      expect(s.filter((x) => x === 1)).toHaveLength(k);
      // the ticked ones are the top-k of the voter's own order
      for (const i of orderOf(aff).slice(0, k)) expect(s[i]).toBe(1);
    }
  });

  it('grades stay inside 1..5 and points always sum to the budget', () => {
    const aff = [0.72, 0.05, 0.95, 0.4];
    for (const contrast of [1, 2, 4]) {
      const g = gradesOf(aff, { contrast });
      for (const x of g) expect(x).toBeGreaterThanOrEqual(1);
      for (const x of g) expect(x).toBeLessThanOrEqual(5);
    }
    for (const concentration of [1, 2, 5]) {
      const p = pointsOf(aff, 10, { concentration });
      expect(p.reduce((a, x) => a + x, 0)).toBe(10);
    }
  });

  it('a more concentrated points ballot never favours a candidate you rank lower', () => {
    const aff = [0.72, 0.05, 0.95, 0.4];
    const spread = pointsOf(aff, 10, { concentration: 1 });
    const focused = pointsOf(aff, 10, { concentration: 5 });
    const fav = orderOf(aff)[0];
    expect(focused[fav]).toBeGreaterThanOrEqual(spread[fav]);
  });

  it('electorate ballots feed the engine for every rule a language allows', () => {
    for (const lang of BALLOT_LANGUAGES) {
      const { ranks, scores } = electorateBallots(ELECTORATE, lang);
      expect(ranks).toHaveLength(ELECTORATE.length);
      for (const rule of RULES_FOR[lang]) {
        const w = ruleWinnerFromRanks(ranks, M, rule, scores);
        expect(w, `${lang}/${rule}`).toBeGreaterThanOrEqual(0);
        expect(w).toBeLessThan(M);
      }
    }
  });
});

describe('votePlay — the fixed election is the one the page promises', () => {
  it('is a genuine centre-squeeze: the language moves the winner', () => {
    const names = (lang: Parameters<typeof winnersFor>[1]) => {
      const w = winnersFor(DEFAULT_YOU, lang, RULES_FOR[lang]);
      return Object.fromEntries(Object.entries(w).map(([r, i]) => [r, CANDIDATES[i]?.name ?? '?']));
    };
    // A single name elects the largest bloc; richer ballots elect the compromise.
    expect(names('one').plurality).toBe('Alice');
    expect(names('approve').approval).toBe('Carla');
    expect(names('points').cumulative).toBe('Carla');
    const rank = names('rank');
    expect(rank.condorcet).toBe('Carla');
    // Within ONE ballot, the methods still disagree — that is the second lesson.
    expect(new Set(Object.values(rank)).size).toBeGreaterThan(1);
  });

  it('elects at least three different people across the languages', () => {
    const all = new Set<string>();
    for (const lang of BALLOT_LANGUAGES) {
      const w = winnersFor(DEFAULT_YOU, lang, RULES_FOR[lang]);
      for (const i of Object.values(w)) all.add(CANDIDATES[i]?.name ?? '?');
    }
    expect(all.size).toBeGreaterThanOrEqual(3);
  });

  it('reports what YOU get, by your own ranking', () => {
    // DEFAULT_YOU ranks Carla first, then Alice, Diane, Bruno.
    expect(yourRankOf(DEFAULT_YOU, 2)).toBe(1); // Carla
    expect(yourRankOf(DEFAULT_YOU, 0)).toBe(2); // Alice
    expect(yourRankOf(DEFAULT_YOU, 1)).toBe(4); // Bruno
    expect(yourRankOf(DEFAULT_YOU, -1)).toBe(0); // no winner
  });
});
