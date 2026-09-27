import { MAP_PADDING, buildScene, censusAt, styleOf, type SceneInput } from './mapScene';
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
      ['party7', 'blue'],
    ]);
    for (const lens of POLITY_LENSES) {
      for (let id = 0; id < 4; id += 1) expect(styleOf(lens, input(), id)).toHaveLength(3);
    }
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

describe('censusAt', () => {
  it('takes the latest census at or before the year, the first otherwise', () => {
    const censuses = [{ year: 0 }, { year: 2 }, { year: 1 }];
    expect(censusAt(censuses, 1)).toEqual({ year: 1 });
    expect(censusAt(censuses, 9)).toEqual({ year: 2 });
    expect(censusAt([{ year: 3 }], 1)).toEqual({ year: 3 });
    expect(censusAt([], 1)).toBeUndefined();
  });
});
