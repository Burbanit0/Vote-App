import { describe, it, expect } from 'vitest';
import {
  BALLOT_LANGUAGES,
  RULES_FOR,
  ballotFrom,
  ballotSpace,
  gradesOf,
  pointsOf,
  orderOf,
  electorateBallots,
} from './ballotLanguages';
import {
  CANDIDATES,
  ELECTORATE,
  ELECTORATE_FIRST_CHOICE,
  DEFAULT_YOU,
  bestResponse,
  pivot,
  winnerWith,
  winnersFor,
  yourRankOf,
} from './votePlay';
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
  it('the first-choice tally is the centre-squeeze the crowd view draws', () => {
    const counts = Object.fromEntries(
      ELECTORATE_FIRST_CHOICE.map((n, i) => [CANDIDATES[i].name, n])
    );
    // The crowd view and its caption depend on these exact camps.
    expect(counts).toEqual({ Alice: 16, Bruno: 15, Carla: 3, Diane: 7 });
    expect(ELECTORATE_FIRST_CHOICE.reduce((a, x) => a + x, 0)).toBe(ELECTORATE.length);
    // The compromise has the smallest first-choice camp yet wins richer methods —
    // that gap is the whole point of showing where you stand.
    const carla = CANDIDATES.findIndex((c) => c.name === 'Carla');
    expect(Math.min(...ELECTORATE_FIRST_CHOICE)).toBe(ELECTORATE_FIRST_CHOICE[carla]);
    expect(winnersFor(DEFAULT_YOU, 'rank', ['condorcet']).condorcet).toBe(carla);
  });

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

  it('winnersFor and winnerWith agree — one code path, two callers', () => {
    for (const lang of BALLOT_LANGUAGES) {
      const mine = ballotFrom(DEFAULT_YOU, lang);
      const bulk = winnersFor(DEFAULT_YOU, lang, RULES_FOR[lang]);
      for (const rule of RULES_FOR[lang]) {
        expect(winnerWith(mine, lang, rule), `${lang}/${rule}`).toBe(bulk[rule]);
      }
    }
  });

  it('reports what YOU get, by your own ranking', () => {
    // DEFAULT_YOU ranks Carla first, then Alice, Diane, Bruno.
    expect(yourRankOf(DEFAULT_YOU, 2)).toBe(1); // Carla
    expect(yourRankOf(DEFAULT_YOU, 0)).toBe(2); // Alice
    expect(yourRankOf(DEFAULT_YOU, 1)).toBe(4); // Bruno
    expect(yourRankOf(DEFAULT_YOU, -1)).toBe(0); // no winner
  });
});

describe('postures — sincere, strategic, abstention', () => {
  const util = (w: number) => (w >= 0 ? DEFAULT_YOU[w] : -Infinity);

  it('the best response is never worse than voting sincerely', () => {
    for (const lang of BALLOT_LANGUAGES) {
      for (const rule of RULES_FOR[lang]) {
        const sincere = winnerWith(ballotFrom(DEFAULT_YOU, lang), lang, rule);
        const best = bestResponse(DEFAULT_YOU, lang, rule);
        expect(util(best.winner), `${lang}/${rule}`).toBeGreaterThanOrEqual(util(sincere));
      }
    }
  });

  it('“sincere is best” means no ballot at all does better — the search was exhaustive', () => {
    for (const lang of BALLOT_LANGUAGES) {
      for (const rule of RULES_FOR[lang]) {
        for (const k of [1, 9, 14]) {
          const best = bestResponse(DEFAULT_YOU, lang, rule, {}, k);
          if (!best.sincereIsBest) continue;
          for (const b of ballotSpace(DEFAULT_YOU, lang)) {
            expect(util(winnerWith(b, lang, rule, k)), `${lang}/${rule}@${k}`).toBeLessThanOrEqual(
              util(best.winner)
            );
          }
        }
      }
    }
  });

  it('when it says lying pays, the lie really elects someone you prefer', () => {
    for (const lang of BALLOT_LANGUAGES) {
      for (const rule of RULES_FOR[lang]) {
        for (const k of [1, 9, 14]) {
          const best = bestResponse(DEFAULT_YOU, lang, rule, {}, k);
          if (best.sincereIsBest) continue;
          const sincere = winnerWith(ballotFrom(DEFAULT_YOU, lang), lang, rule, k);
          expect(util(best.winner), `${lang}/${rule}@${k}`).toBeGreaterThan(util(sincere));
          // and the claimed ballot is the one that does it
          expect(winnerWith(best.ballot, lang, rule, k)).toBe(best.winner);
        }
      }
    }
  });

  it('one ballot alone is not pivotal here — and the page must not pretend it is', () => {
    // 41 sincere voters, one of you: no language, no rule, no lie changes anything.
    // Saying so is the honest setup for the question that follows: how many of us?
    for (const lang of BALLOT_LANGUAGES) {
      for (const rule of RULES_FOR[lang]) {
        expect(bestResponse(DEFAULT_YOU, lang, rule, {}, 1).sincereIsBest, `${lang}/${rule}`).toBe(
          true
        );
      }
    }
  });

  it('counts how many voters like you it takes, and the count varies by method', () => {
    const flips = RULES_FOR.rank.map((r) => pivot(DEFAULT_YOU, 'rank', r).toFlip);
    // Plurality needs a big camp; the runoff rules move on half of it; the Condorcet
    // family already elects your favourite, so no camp is needed at all.
    expect(pivot(DEFAULT_YOU, 'one', 'plurality').toFlip).toBe(14);
    expect(pivot(DEFAULT_YOU, 'rank', 'two_round').toFlip).toBe(7);
    expect(new Set(flips).size).toBeGreaterThan(1);
  });

  it('a camp large enough really does elect someone else', () => {
    const k = pivot(DEFAULT_YOU, 'one', 'plurality').toFlip;
    const mine = ballotFrom(DEFAULT_YOU, 'one');
    expect(winnerWith(mine, 'one', 'plurality', k - 1)).toBe(winnerWith(null, 'one', 'plurality'));
    expect(winnerWith(mine, 'one', 'plurality', k)).not.toBe(winnerWith(null, 'one', 'plurality'));
  });

  it('the incentive to lie depends on the METHOD, not on the voter', () => {
    // Same opinion, same paper, same camp size — IRV rewards a compromise ballot and
    // the Condorcet family does not. That split is the point of the posture control.
    const tempts = RULES_FOR.rank.map((r) => pivot(DEFAULT_YOU, 'rank', r).toTempt > 0);
    expect(tempts.some(Boolean)).toBe(true);
    expect(tempts.some((x) => !x)).toBe(true);
    expect(pivot(DEFAULT_YOU, 'rank', 'irv').toTempt).toBe(9);
  });

  it('turnout is not monotone under IRV — one more of you can make it worse for you', () => {
    // The no-show paradox, live in this fixture: a camp of 8 elects Alice (your 2nd
    // choice), a camp of 9 elects Bruno (your last). This is why `pivot` scans from 1
    // instead of bisecting, and it is the reason the page shows the count at all.
    const mine = ballotFrom(DEFAULT_YOU, 'rank');
    const at = (k: number) => winnerWith(mine, 'rank', 'irv', k);
    expect(CANDIDATES[at(8)].name).toBe('Alice');
    expect(CANDIDATES[at(9)].name).toBe('Bruno');
    expect(DEFAULT_YOU[at(9)]).toBeLessThan(DEFAULT_YOU[at(8)]);
  });

  it('abstaining removes exactly one ballot — the electorate still elects someone', () => {
    for (const lang of BALLOT_LANGUAGES) {
      for (const rule of RULES_FOR[lang]) {
        const w = winnerWith(null, lang, rule);
        expect(w, `${lang}/${rule}`).toBeGreaterThanOrEqual(0);
        expect(w).toBeLessThan(CANDIDATES.length);
      }
    }
  });
});
