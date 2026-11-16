// What the CLIENT does with a truncated ballot and with equal ranks, today, set beside the backend's.
//
// This pins a state of affairs; it is not a convention (docs/spec/truncated-ballots.md, work order
// P3-5). The backend's answers are in __fixtures__/truncatedBallots.json, which
// fast_api_voter/scripts/gen_truncated_ballots.py generates from its own rules (and
// api/tests/test_truncated_ballots_fixture.py keeps in step); the client's are computed here. The
// page's tables are parsed at the bottom and checked cell by cell against both, so a number in them
// is one a test measured.
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, it, expect } from 'vitest';
import fixtureJson from './__fixtures__/truncatedBallots.json';
import { computeRanks, pairwise, ruleWinnerFromRanks, type Rule } from './playgroundVoting';

interface Fixture {
  candidates: string[];
  truncated: { profiles: string[][][]; backend: Record<string, string[]> };
  probes: Record<
    'duel' | 'field',
    { ballots: string[][]; backend: Record<string, string | string[]> }
  >;
  equalRanks: {
    candidates: Record<string, [number, number]>;
    voters: Array<[number, number]>;
    listings: Record<'listed' | 'reversed', string[]>;
    backend: Record<'listed' | 'reversed', Record<string, string>>;
  };
  scores: { ballots: number[][]; backend: Record<string, string> };
  shared: {
    approvalGrade: number;
    cases: Array<{ places: number; grades: number[][]; backend: Record<string, string> }>;
  };
  scoreTies: {
    grades: number[][];
    listings: Record<'listed' | 'reversed', string[]>;
    backend: Record<'listed' | 'reversed', Record<string, string>>;
  };
}
const fixture = fixtureJson as unknown as Fixture;
const NAMES = fixture.candidates;
const ORDINAL = Object.keys(fixture.truncated.backend);
const SEVEN = ['score', 'star', 'cumulative', 'maximin', 'nash', 'approval', 'majority_judgment'];

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

/** The rules that read one shared duel count (backend `_pairwise_wins`; client `pairwise()`). */
const PAIRWISE = [
  'condorcet',
  'minimax',
  'schulze',
  'ranked_pairs',
  'kemeny',
  'black',
  'raynaud',
  'benham',
  'river',
  'smith_irv',
  'split_cycle',
];
const POSITIONAL = ['borda', 'nanson', 'baldwin'];

/** The client's winner when ranks list only the named candidates, the field listed as `order`. */
function clientWinner(
  ballots: string[][],
  rule: string,
  order: string[] = NAMES,
  scores?: number[][]
): string {
  const ranks = ballots.map((ballot) => ballot.map((name) => order.indexOf(name)));
  return order[ruleWinnerFromRanks(ranks, order.length, rule as Rule, scores, order)];
}

function permutations<T>(items: T[]): T[][] {
  if (items.length <= 1) return [items];
  return items.flatMap((x, i) =>
    permutations([...items.slice(0, i), ...items.slice(i + 1)]).map((rest) => [x, ...rest])
  );
}

/** Every winner the client gives for the probe, over all 24 listings of the field. */
function winnersOverListings(ballots: string[][], rule: string): string[] {
  const all = permutations(NAMES).map((order) => clientWinner(ballots, rule, order));
  return [...new Set(all)].sort();
}

function shortBallotDisagreements(rule: string): number {
  return fixture.truncated.profiles.filter(
    (profile, i) => clientWinner(profile, rule) !== fixture.truncated.backend[rule][i]
  ).length;
}

/** A score ballot's ranks (best to worst), which the cardinal rules ignore but the call needs. */
const ranksOf = (scores: number[][]): number[][] =>
  scores.map((s) => [0, 1, 2, 3].sort((a, b) => s[b] - s[a]));

/** The client's winner of a score matrix whose columns are the field listed as `order`. */
function clientScoreWinner(rule: string, scores: number[][], order: string[] = NAMES): string {
  return order[ruleWinnerFromRanks(ranksOf(scores), order.length, rule as Rule, scores, order)];
}

const approvals = (grades: number[][]): number[][] =>
  grades.map((row) => row.map((g) => (g >= fixture.shared.approvalGrade ? 1 : 0)));

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

/** The seven rules' winners when A and B are graded alike, the field listed as `order`. */
function clientTieWinners(label: 'listed' | 'reversed'): Record<string, string> {
  const order = fixture.scoreTies.listings[label];
  const grades = fixture.scoreTies.grades.map((row) => order.map((n) => row[NAMES.indexOf(n)]));
  return Object.fromEntries(
    SEVEN.map((rule) => [
      rule,
      clientScoreWinner(rule, rule === 'approval' ? approvals(grades) : grades, order),
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

describe('the "duel" probe: no rule is decided by a lot on the backend', () => {
  // Three bullet votes for A, two ballots B then C: [[A], [A], [A], [B, C], [B, C]].
  const { ballots, backend } = fixture.probes.duel;

  it.each(ORDINAL)('%s: the winners over every listing of the field', (rule) => {
    const expected = { anti_plurality: 'D' }[rule as 'anti_plurality'] ?? 'A';
    expect(winnersOverListings(ballots, rule).join('')).toBe(
      PAIRWISE.includes(rule) ? 'ABCD' : expected
    );
  });

  it('the pairwise rules: the backend elects A, the client counts a left-out candidate as top', () => {
    // Position 0 for a candidate a ballot leaves out, and a tie in position goes to the later-listed:
    // the count depends on the listing, so any of the four wins.
    expect(pairwise([[0, 1], [2]], 3)).toEqual([
      [0, 1, 0],
      [1, 0, 0],
      [2, 2, 0],
    ]);
    for (const rule of PAIRWISE) expect(backend[rule], rule).toBe('A');
  });

  it('Borda, Nanson and Baldwin give a bullet vote the points of a first place on the whole field', () => {
    for (const rule of POSITIONAL) {
      expect(backend[rule], rule).toBe('B');
      expect(clientWinner(ballots, rule), rule).toBe('A');
    }
  });

  it('anti-plurality: the backend vetoes only candidates a ballot ranks, the client has a field of four', () => {
    expect(backend.anti_plurality).toBe('B');
    expect(clientWinner(ballots, 'anti_plurality')).toBe('D');
  });
});

describe('the "field" probe: a candidate no ballot ranks', () => {
  const { ballots, backend } = fixture.probes.field;

  it.each(['anti_plurality', 'coombs'])(
    '%s: the client elects the unranked A, the backend never',
    (rule) => {
      expect(ballots.flat()).not.toContain('A');
      expect(clientWinner(ballots, rule)).toBe('A');
      expect(backend[rule]).not.toContain('A');
    }
  );
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
    expect(clientScoreWinner(rule, fixture.scores.ballots)).toBe(fixture.scores.backend[rule]);
  });
});

describe('a ballot cut to its top places, handed to approval and majority judgment as 0/1 and grades', () => {
  it.each(SEVEN.slice(5))('%s: both engines read it alike', (rule) => {
    for (const { grades, backend } of fixture.shared.cases) {
      const ballot = rule === 'approval' ? approvals(grades) : grades;
      expect(clientScoreWinner(rule, ballot)).toBe(backend[rule]);
    }
  });
});

describe('equal scores: a tie between A and B is drawn alike, whichever way the field is listed', () => {
  it.each(SEVEN)('%s', (rule) => {
    const { backend } = fixture.scoreTies;
    expect(clientTieWinners('listed')[rule]).toBe(backend.listed[rule]);
    expect(clientTieWinners('reversed')[rule]).toBe(backend.reversed[rule]);
    expect(backend.listed[rule]).toBe(backend.reversed[rule]);
  });
});

describe('docs/spec/truncated-ballots.md says what ran', () => {
  const doc = readFileSync(
    resolve(__dirname, '../../../docs/spec/truncated-ballots.md'),
    'utf8'
  ).replace(/\r\n/g, '\n');
  const rows = (pattern: RegExp): string[][] =>
    doc
      .split('\n')
      .map((line) => pattern.exec(line))
      .filter((m): m is RegExpExecArray => m !== null)
      .map((m) => m.slice(1));
  const yes = (b: boolean) => (b ? 'yes' : 'no');
  const listed = equalRankWinners(fixture.equalRanks.listings.listed);
  const reversed = equalRankWinners(fixture.equalRanks.listings.reversed);
  const clientListed = clientTieWinners('listed');
  const clientReversed = clientTieWinners('reversed');
  const list = (xs: string[]) => xs.join(', ');

  it('the ordinal table has a row per rule, and every cell is what the tests above measured', () => {
    const table = rows(
      /^\| `(\w+)` \| [^|]+ \| ([A-D]) \| ([A-D](?:, [A-D])*) \| (yes|no) \| (\d+)\/60 \| (yes|no) \| (yes|no) \| (yes|no) \|$/
    );
    expect(table.map((r) => r[0]).sort()).toEqual([...ORDINAL].sort());
    for (const [rule, backendDuel, clientDuel, sameDuel, disagree, ...equal] of table) {
      const { duel } = fixture.probes;
      const measuredClient = winnersOverListings(duel.ballots, rule);
      const backend = fixture.equalRanks.backend;
      expect(backendDuel, rule).toBe(duel.backend[rule]);
      expect(clientDuel, rule).toBe(list(measuredClient));
      expect(sameDuel, rule).toBe(
        yes(measuredClient.length === 1 && measuredClient[0] === backendDuel)
      );
      expect(disagree, rule).toBe(String(shortBallotDisagreements(rule)));
      expect(equal, rule).toEqual([
        yes(backend.listed[rule] !== backend.reversed[rule]),
        yes(listed[rule] !== reversed[rule]),
        yes(backend.listed[rule] === listed[rule] && backend.reversed[rule] === reversed[rule]),
      ]);
    }
  });

  it('the field rows give what the backend never elects and the client does', () => {
    const table = rows(
      /^\| `(anti_plurality|coombs)` \| ([A-D](?:, [A-D])*) \| ([A-D]) \| (yes|no) \|$/
    );
    expect(table.map((r) => r[0]).sort()).toEqual(['anti_plurality', 'coombs']);
    for (const [rule, backend, client, same] of table) {
      const { ballots } = fixture.probes.field;
      expect(backend, rule).toBe(list(fixture.probes.field.backend[rule] as string[]));
      expect(client, rule).toBe(clientWinner(ballots, rule));
      expect(same, rule).toBe('no');
    }
  });

  it('the score rows give the winners both engines elect on the cut ballot', () => {
    const table = rows(
      /^\| `(score|star|cumulative|maximin|nash)` \| ([A-D]) \| ([A-D]) \| (yes|no) \|$/
    );
    expect(table.map((r) => r[0]).sort()).toEqual(Object.keys(fixture.scores.backend).sort());
    for (const [rule, backend, client, same] of table) {
      expect(backend, rule).toBe(fixture.scores.backend[rule]);
      expect(client, rule).toBe(clientScoreWinner(rule, fixture.scores.ballots));
      expect(same, rule).toBe(yes(backend === client));
    }
  });

  it('the approval and majority-judgment rows give the winner for the whole ballot, cut to 1 and to 2', () => {
    const table = rows(
      /^\| `(approval|majority_judgment)` \| ([A-D]) \| ([A-D]) \| ([A-D]) \| (yes|no) \|$/
    );
    expect(table.map((r) => r[0]).sort()).toEqual(['approval', 'majority_judgment']);
    for (const [rule, ...cells] of table) {
      const byPlaces = Object.fromEntries(fixture.shared.cases.map((c) => [c.places, c]));
      const backend = [4, 1, 2].map((p) => byPlaces[p].backend[rule]);
      const client = [4, 1, 2].map((p) =>
        clientScoreWinner(
          rule,
          rule === 'approval' ? approvals(byPlaces[p].grades) : byPlaces[p].grades
        )
      );
      expect(cells.slice(0, 3), rule).toEqual(backend);
      expect(cells[3], rule).toBe(yes(backend.join() === client.join()));
    }
  });

  it('the equal-scores rows give the winner of the tie, listed and reversed, on both engines', () => {
    const table = rows(/^\| `(\w+)` \| ([A-D]), ([A-D]) \| ([A-D]), ([A-D]) \| (yes|no) \|$/);
    expect(table.map((r) => r[0]).sort()).toEqual([...SEVEN].sort());
    for (const [rule, bl, br, cl, cr, same] of table) {
      const { backend } = fixture.scoreTies;
      expect([bl, br], rule).toEqual([backend.listed[rule], backend.reversed[rule]]);
      expect([cl, cr], rule).toEqual([clientListed[rule], clientReversed[rule]]);
      expect(same, rule).toBe(yes(bl === cl && br === cr));
    }
  });
});
