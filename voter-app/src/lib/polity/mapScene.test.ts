import {
  MAP_PADDING,
  buildScene,
  censusAt,
  partyStyles,
  styleOf,
  type SceneInput,
} from './mapScene';
import { POLITY_LENSES } from './urlState';

const input = (overrides: Partial<SceneInput> = {}): SceneInput => ({
  citizens: [
    [0, 0],
    [2, 0],
    [0, 1],
    [2, 1],
  ],
  frame: {
    status: [0, 1, 2, 0],
    chamber: [0, 0, 0, 1],
    act: [-1, 0, 3, 4],
    vote: [-1, 0, 1, 2],
    candidacy: [-1, 0, 2, 4],
  },
  citizenParties: [0, 1, null, 7],
  partyStyle: partyStyles([{ parties: [0, 1, null, 7] }]),
  parties: [
    { party_id: 0, xy: [0.5, 0.5] },
    { party_id: 1, xy: [1.5, 0.5] },
  ],
  president: { citizen_id: 2, xy: [0.2, 0.9], pledged_xy: [0.1, 1] },
  ...overrides,
});

describe('population map scene', () => {
  it('fits every point inside the padding with one scale for both axes, up positive', () => {
    const scene = buildScene(input(), 'activity', 248, 148);
    const xs = scene.points.map((p) => p.x);
    const ys = scene.points.map((p) => p.y);
    expect(Math.min(...xs)).toBeCloseTo(MAP_PADDING);
    expect(Math.max(...xs)).toBeCloseTo(248 - MAP_PADDING);
    // 2 wide by 1 tall at scale 100: centred vertically.
    expect(Math.max(...ys) - Math.min(...ys)).toBeCloseTo(100);
    expect(scene.points[2].y).toBeLessThan(scene.points[0].y); // (0, 1) is above (0, 0)
    expect(scene.project([1, 0.5])).toEqual([124, 74]);
  });

  it('places parties, the president and their pledge on the same projection', () => {
    const scene = buildScene(input(), 'activity', 248, 148);
    expect(scene.parties.map((p) => [p.partyId, p.x, p.y, p.color])).toEqual([
      [0, ...scene.project([0.5, 0.5]), 'blue'],
      [1, ...scene.project([1.5, 0.5]), 'orange'],
    ]);
    const [x, y] = scene.project([0.2, 0.9]);
    const [px, py] = scene.project([0.1, 1]);
    expect(scene.president).toEqual({ id: 2, x, y, pledgedX: px, pledgedY: py });
    expect(
      buildScene(
        input({ president: { citizen_id: 2, xy: [0, 0], pledged_xy: null } }),
        'activity',
        248,
        148
      ).president
    ).toMatchObject({ pledgedX: null, pledgedY: null });
    expect(buildScene(input({ president: null }), 'activity', 248, 148).president).toBeNull();
  });

  it('draws, and sizes the map by, only the parties with members at this census', () => {
    // Party 9 was founded and dissolved elsewhere in the run: nobody belongs to it now.
    const gone = { party_id: 9, xy: [50, 50] };
    const scene = buildScene(
      input({ citizenParties: [1, 1, null, 7], parties: [...input().parties, gone] }),
      'activity',
      248,
      148
    );
    expect(scene.parties.map((p) => p.partyId)).toEqual([1]);
    expect(scene.points.map((p) => p.party)).toEqual([1, 1, null, 7]);
    expect(scene.project([1, 0.5])).toEqual([124, 74]); // party 9 does not stretch the map
  });

  it('gives every code of every lens a shape and a colour, and counts the legend', () => {
    const scene = buildScene(input(), 'activity', 248, 148);
    expect(scene.points.map((p) => p.legend)).toEqual([
      'elector',
      'candidate',
      'elected',
      'chamber',
    ]);
    expect(scene.legend.map((l) => [l.key, l.count])).toEqual([
      ['elector', 1],
      ['candidate', 1],
      ['elected', 1],
      ['chamber', 1],
    ]);
    expect(buildScene(input(), 'act', 248, 148).points.map((p) => [p.legend, p.shape])).toEqual([
      ['notConsulted', 'circle'],
      ['nothing', 'ring'],
      ['mobilize', 'square'],
      ['waitForElection', 'cross'],
    ]);
    expect(buildScene(input(), 'vote', 248, 148).points.map((p) => p.legend)).toEqual([
      'noBallot',
      'blank',
      'forWinner',
      'forOther',
    ]);
    expect(buildScene(input(), 'candidacy', 248, 148).points.map((p) => p.legend)).toEqual([
      'notAsked',
      'declined',
      'nominationLost',
      'electedCandidate',
    ]);
    expect(buildScene(input(), 'party', 248, 148).points.map((p) => [p.legend, p.color])).toEqual([
      ['party0', 'blue'],
      ['party1', 'orange'],
      ['noParty', 'muted'],
      ['party7', 'green'], // its own colour: no longer party 0's blue, as 7 % 7 made it
    ]);
    for (const lens of POLITY_LENSES) {
      for (let id = 0; id < 4; id += 1) expect(styleOf(lens, input(), id)).toHaveLength(3);
    }
  });

  it('lists the party legend by number, independents last, whatever order citizens meet them in', () => {
    // Met first: party 7, then 1, an independent, then 0 -- the order the legend used to keep.
    const meetsSevenFirst = { citizenParties: [7, 1, null, 0] };
    const scene = buildScene(
      input({ ...meetsSevenFirst, partyStyle: partyStyles([{ parties: [7, 1, null, 0] }]) }),
      'party',
      248,
      148
    );
    expect(scene.legend.map((l) => l.key)).toEqual(['party0', 'party1', 'party7', 'noParty']);
  });

  it('falls back on a code it does not know and on an empty population', () => {
    const odd = input({
      frame: { status: [9], chamber: [0], act: [9], vote: [9], candidacy: [9] },
      citizens: [[0, 0]],
    });
    expect(styleOf('activity', odd, 0)[0]).toBe('elector');
    expect(styleOf('act', odd, 0)[0]).toBe('notConsulted');
    expect(styleOf('vote', odd, 0)[0]).toBe('noBallot');
    expect(styleOf('candidacy', odd, 0)[0]).toBe('notAsked');
    const empty = buildScene(
      input({ citizens: [], parties: [], president: null }),
      'activity',
      100,
      100
    );
    expect(empty.points).toEqual([]);
    expect(empty.project([0, 0])).toEqual([50, 50]);
  });
});

describe('partyStyles', () => {
  const census = (...parties: (number | null)[]) => ({ parties });
  const look = (style: ReturnType<typeof partyStyles>, party: number) => {
    const { shape, color } = style(party);
    return `${color} ${shape}`;
  };

  it('gives up to six parties at once a colour each, all of them dots', () => {
    const style = partyStyles([census(0, 1, 2, 3, 4, 5, null)]);
    expect([0, 1, 2, 3, 4, 5].map((party) => look(style, party))).toEqual([
      'blue circle',
      'orange circle',
      'green circle',
      'purple circle',
      'sky circle',
      'vermillion circle',
    ]);
  });

  it('tells apart by shape the parties past the colours', () => {
    const style = partyStyles([census(...Array.from({ length: 14 }, (_, i) => i))]);
    expect([6, 7, 12, 13].map((party) => look(style, party))).toEqual([
      'blue square',
      'orange square',
      'blue triangle',
      'orange triangle',
    ]);
  });

  it('keeps a party its style for life, and passes on a dissolved one’s', () => {
    // Party 9 lives in censuses 0-2 and party 20 is founded once 9 is gone; 21 overlaps 9.
    const style = partyStyles([census(0, 9), census(9, 0, 21), census(9, 21), census(20, 21)]);
    expect(look(style, 9)).toBe('orange circle');
    expect(look(style, 21)).toBe('green circle'); // alive with 0 and 9: neither's style
    expect(look(style, 20)).toBe('blue circle'); // 0 and 9 are gone: the first free style
    expect(look(style, 42)).toBe(look(partyStyles([]), 42)); // no census shows it: by its id
  });
});

describe('censusAt', () => {
  it('takes the latest census at or before the year, the first otherwise', () => {
    const censuses = [{ year: 0 }, { year: 2 }, { year: 1 }];
    expect(censusAt(censuses, 1)).toEqual({ year: 1 });
    expect(censusAt(censuses, 9)).toEqual({ year: 2 });
    expect(censusAt([{ year: 3 }], 1)).toEqual({ year: 3 });
    expect(censusAt([], 1)).toBeUndefined();
  });
});
