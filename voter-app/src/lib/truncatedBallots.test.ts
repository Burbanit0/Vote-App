// What the CLIENT does with a truncated ballot and with equal ranks, today, set beside the backend's.
//
// This pins a state of affairs; it is not a convention (docs/spec/truncated-ballots.md, work order
// P3-5). The backend's answers are in __fixtures__/truncatedBallots.json, which
// fast_api_voter/scripts/gen_truncated_ballots.py generates from its own rules (and
// api/tests/test_truncated_ballots_as_is.py keeps in step); the client's are computed here and
// pinned, row by row, in the tables below. The page's own tables are checked against both at the
// bottom, so a number in it is one that ran.
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, it, expect } from 'vitest';
import fixtureJson from './__fixtures__/truncatedBallots.json';
import { computeRanks, pairwise, ruleWinnerFromRanks, type Rule } from './playgroundVoting';

interface Fixture {
  candidates: string[];
  truncated: { profiles: string[][][]; backend: Record<string, string[]> };
  equalRanks: {
    candidates: Record<string, [number, number]>;
    voters: Array<[number, number]>;
    listings: Record<'listed' | 'reversed', string[]>;
    backend: Record<'listed' | 'reversed', Record<string, string>>;
  };
  scores: { ballots: number[][]; backend: Record<string, string> };
}
const fixture = fixtureJson as unknown as Fixture;
const NAMES = fixture.candidates;
const ORDINAL = Object.keys(fixture.truncated.backend);

/** Per rule: on how many of the 60 short-ballot profiles the two engines elect different people. */
const DISAGREEMENTS: Record<string, number> = {
  plurality: 0,
  two_round: 0,
  irv: 0,
  bucklin: 0,
  dowdall: 0,
  coombs: 0,
  anti_plurality: 1,
  borda: 24,
  nanson: 32,
  baldwin: 33,
  condorcet: 43,
  minimax: 45,
  schulze: 40,
  ranked_pairs: 40,
  kemeny: 41,
  black: 37,
  raynaud: 38,
  benham: 38,
  river: 40,
  smith_irv: 34,
  split_cycle: 36,
};

const clientWinner = (ranks: number[][], rule: string, scores?: number[][]): string =>
  NAMES[ruleWinnerFromRanks(ranks, NAMES.length, rule as Rule, scores, NAMES)];

function shortBallotDisagreements(rule: string): number {
  return fixture.truncated.profiles.filter((profile, i) => {
    const ranks = profile.map((ballot) => ballot.map((name) => NAMES.indexOf(name)));
    return clientWinner(ranks, rule) !== fixture.truncated.backend[rule][i];
  }).length;
}

/** The client's winner for the equal-ranks voters, with the candidates listed in `order`. */
function equalRankWinners(order: string[]): Record<string, string> {
  const voters = fixture.equalRanks.voters.map(([x, y]) => ({ x, y }));
  const cands = order.map((n) => ({
    x: fixture.equalRanks.candidates[n][0],
    y: fixture.equalRanks.candidates[n][1],
  }));
  const ranks = computeRanks(voters, cands);
  return Object.fromEntries(
    ORDINAL.map((rule) => [
      rule,
      order[ruleWinnerFromRanks(ranks, 4, rule as Rule, undefined, order)],
    ])
  );
}

describe('short ballots: the client, against the backend, rule by rule', () => {
  it('covers the 21 ordinal rules over 60 profiles', () => {
    expect(ORDINAL).toHaveLength(21);
    expect(Object.keys(DISAGREEMENTS).sort()).toEqual([...ORDINAL].sort());
    expect(fixture.truncated.profiles).toHaveLength(60);
  });

  it.each(ORDINAL)('%s', (rule) => {
    expect(shortBallotDisagreements(rule)).toBe(DISAGREEMENTS[rule]);
  });
});

describe('the readings, in the client', () => {
  it('a duel with a candidate a ballot leaves out: position 0, the top, and a tie goes to the later-listed', () => {
    // Ballot 1 ranks A then B and leaves C out; ballot 2 ranks only C. The backend's count of the
    // same ballots is [[0,1,1],[0,0,1],[1,1,0]]: nothing between A and B from ballot 2, and C below
    // A and B in ballot 1. Here C is above A and B in both ballots, and A against B is the listing's.
    expect(pairwise([[0, 1], [2]], 3)).toEqual([
      [0, 1, 0],
      [1, 0, 0],
      [2, 2, 0],
    ]);
  });

  it('Borda gives a one-place ballot the points of a first place on the whole field', () => {
    // The backend elects B on [[A], [B, C]] (a bullet vote is worth nothing there): here A is worth m - 1.
    const names = ['A', 'B', 'C'];
    expect(names[ruleWinnerFromRanks([[0], [1, 2]], 3, 'borda', undefined, names)]).toBe('A');
    expect(names[ruleWinnerFromRanks([[0], [1, 2], [0]], 3, 'dowdall', undefined, names)]).toBe(
      'A'
    );
  });

  it('a candidate no ballot ranks is still in the field', () => {
    // Nobody ranks A (index 0) on profile 8: never vetoed, it wins anti-plurality here; the backend
    // elects C, which never sees A.
    const ranks = fixture.truncated.profiles[8].map((b) => b.map((n) => NAMES.indexOf(n)));
    expect(fixture.truncated.profiles[8].flat()).not.toContain('A');
    expect(clientWinner(ranks, 'anti_plurality')).toBe('A');
    expect(fixture.truncated.backend.anti_plurality[8]).toBe('C');
  });
});

describe('equal ranks: the client follows the listing, the backend does not', () => {
  const listed = equalRankWinners(fixture.equalRanks.listings.listed);
  const reversed = equalRankWinners(fixture.equalRanks.listings.reversed);

  it.each(ORDINAL)("%s: reversing the candidates changes the client's winner", (rule) => {
    expect(listed[rule]).not.toBe(reversed[rule]);
  });

  it.each(ORDINAL)("%s: the backend's does not change, and the engines differ", (rule) => {
    const backend = fixture.equalRanks.backend;
    expect(backend.listed[rule]).toBe(backend.reversed[rule]);
    expect([listed[rule], reversed[rule]]).not.toEqual([
      backend.listed[rule],
      backend.reversed[rule],
    ]);
  });
});

describe('a truncated score ballot: the five score rules count the zeros the same way', () => {
  it.each(Object.keys(fixture.scores.backend))('%s', (rule) => {
    const scores = fixture.scores.ballots;
    const ranks = scores.map((s) => [0, 1, 2, 3].sort((a, b) => s[b] - s[a]));
    expect(clientWinner(ranks, rule, scores)).toBe(fixture.scores.backend[rule]);
  });
});

describe('docs/spec/truncated-ballots.md says what ran', () => {
  const doc = readFileSync(resolve(process.cwd(), '../docs/spec/truncated-ballots.md'), 'utf8');
  const rows = (pattern: RegExp): string[][] =>
    doc
      .split('\n')
      .map((line) => pattern.exec(line))
      .filter((m): m is RegExpExecArray => m !== null)
      .map((m) => m.slice(1));

  const listed = equalRankWinners(fixture.equalRanks.listings.listed);
  const reversed = equalRankWinners(fixture.equalRanks.listings.reversed);
  const yes = (b: boolean) => (b ? 'yes' : 'no');

  it('the ordinal table has a row per rule, and every cell is what the tests above measured', () => {
    const table = rows(
      /^\| `(\w+)` \| [^|]+ \| (\d+)\/60 \| (yes|no) \| (yes|no) \| (yes|no) \| (yes|no) \|$/
    );
    expect(table.map((r) => r[0]).sort()).toEqual([...ORDINAL].sort());
    for (const [rule, disagree, sameShort, backendFollows, clientFollows, sameEqual] of table) {
      const backend = fixture.equalRanks.backend;
      const measured = [
        String(shortBallotDisagreements(rule)),
        yes(shortBallotDisagreements(rule) === 0),
        yes(backend.listed[rule] !== backend.reversed[rule]),
        yes(listed[rule] !== reversed[rule]),
        yes(backend.listed[rule] === listed[rule] && backend.reversed[rule] === reversed[rule]),
      ];
      expect([disagree, sameShort, backendFollows, clientFollows, sameEqual], rule).toEqual(
        measured
      );
    }
  });

  it('the score rows give the winners both engines elect', () => {
    const table = rows(
      /^\| `(score|star|cumulative|maximin|nash)` \| [^|]+ \| elects (\w) \| elects (\w) \| (yes|no) \|$/
    );
    expect(table.map((r) => r[0]).sort()).toEqual(Object.keys(fixture.scores.backend).sort());
    for (const [rule, backend, client, same] of table) {
      expect(backend, rule).toBe(fixture.scores.backend[rule]);
      expect(client, rule).toBe(fixture.scores.backend[rule]);
      expect(same).toBe('yes');
    }
  });
});
