import {
  LANE_HEIGHT,
  TIMELINE_LANES,
  TIMELINE_PADDING,
  glyphOf,
  layoutTimeline,
  tickAtX,
} from './timelineLayout';

const TERMS = [
  { holder: 2, start_tick: 0, end_tick: 9, ended_by: 'legitimacy_floor' },
  { holder: 21, start_tick: 10, end_tick: 11, ended_by: 'legitimacy_floor' },
  { holder: 2, start_tick: 12, end_tick: 12, ended_by: 'run_end' },
];

describe('timeline layout', () => {
  it('spreads ticks across the width inside its padding', () => {
    const geometry = layoutTimeline([], [], 12, 124);
    expect(geometry.tickX(0)).toBe(TIMELINE_PADDING);
    expect(geometry.tickX(12)).toBe(124 - TIMELINE_PADDING);
    expect(geometry.height).toBe(2 * TIMELINE_PADDING + TIMELINE_LANES.length * LANE_HEIGHT);
    expect(layoutTimeline([], [], 0, 0).tickX(0)).toBe(TIMELINE_PADDING);
  });

  it('draws a term as a band, a run-end term to its last tick and a short one visibly', () => {
    const { bands, tickX } = layoutTimeline(TERMS, [], 12, 124);
    expect(bands[0]).toMatchObject({
      holder: 2,
      x: tickX(0),
      width: tickX(9) - tickX(0),
      endedBy: 'legitimacy_floor',
    });
    expect(bands[1].width).toBe(tickX(11) - tickX(10));
    expect(bands[2].width).toBe(2); // starts and ends at the last tick
  });

  it('marks the ticks no term covers as a vacant presidency', () => {
    const { vacancies, tickX } = layoutTimeline(TERMS, [], 12, 124);
    // Recalled at 9, next elected at 10; recalled at 11, next at 12.
    expect(vacancies.map((v) => [v.startTick, v.endTick])).toEqual([
      [9, 10],
      [11, 12],
    ]);
    expect(vacancies[0]).toMatchObject({ x: tickX(9), width: tickX(10) - tickX(9) });
    // Nobody elected before tick 4, and the last term ends three ticks before the run does.
    const late = [{ holder: 1, start_tick: 4, end_tick: 9, ended_by: 'legitimacy_floor' }];
    expect(
      layoutTimeline(late, [], 12, 124).vacancies.map((v) => [v.startTick, v.endTick])
    ).toEqual([
      [0, 4],
      [9, 12],
    ]);
    expect(layoutTimeline([], [], 12, 124).vacancies).toHaveLength(1);
  });

  it('puts events in their lane and stacks those that share a tick', () => {
    const { glyphs, laneY } = layoutTimeline(
      [],
      [
        { tick: 9, event_type: 'recalled', citizen_id: 2 },
        { tick: 9, event_type: 'snap_election_triggered', citizen_id: null },
        { tick: 9, event_type: 'petition_expired' },
        { tick: 3, event_type: 'something_new' },
      ],
      12,
      124
    );
    expect(glyphs.map((g) => [g.lane, g.kind])).toEqual([
      ['accountability', 'recall'],
      ['elections', 'snap'],
      ['accountability', 'petition'],
      ['society', 'other'],
    ]);
    expect(glyphs[0].y).toBe(laneY.accountability);
    expect(glyphs[2].y).toBe(laneY.accountability + 5);
    expect(glyphs[0].citizenId).toBe(2);
    expect(glyphs[2].citizenId).toBeNull();
  });

  it('knows every institutional event the API sends', () => {
    for (const type of [
      'elected',
      'election_no_winner',
      'election_invalidated',
      'legislative_result',
      'confidence_vote_triggered',
      'confidence_vote_result',
      'petition_launched',
      'bill_proposed',
      'bill_enacted',
      'bill_blocked',
      'coalition_formed',
      'coalition_failed',
      'scandal_occurred',
      'economic_shock_tick',
      'sortition_rotation',
      'constitution_amended',
      'amendment_proposed',
      'amendment_resolved',
      'referendum_held',
      'extra_legal_act',
      'campaign_run',
      'party_founded',
      'party_dissolved',
    ]) {
      expect(glyphOf(type)[1]).not.toBe('other');
    }
  });

  it('keeps a long stack inside its lane, so an election tick of campaigns hides nothing below', () => {
    // Ten nominees campaigning on one tick: at the old fixed 5px a glyph, the stack ran 45px down,
    // through two lanes beneath it.
    const campaigns = Array.from({ length: 10 }, () => ({ tick: 8, event_type: 'campaign_run' }));
    const { glyphs, laneY } = layoutTimeline([], campaigns, 12, 400);
    const ys = glyphs.map((g) => g.y);
    expect(ys[0]).toBe(laneY.elections);
    expect(Math.max(...ys) - laneY.elections).toBeLessThanOrEqual(LANE_HEIGHT / 2 - 5);
    expect(new Set(ys).size).toBe(10); // still one distinct glyph per event, not collapsed
    expect(Math.max(...ys)).toBeLessThan(laneY.accountability - 5); // clear of the next lane's glyphs
  });

  it('files the Phase 5 acts where they belong, not with the society marks', () => {
    // Before they had glyphs both fell through to ['society', 'other'] and read as noise.
    expect(glyphOf('extra_legal_act')).toEqual(['accountability', 'extraLegal']);
    expect(glyphOf('campaign_run')).toEqual(['elections', 'campaign']);
    expect(glyphOf('party_founded')).toEqual(['society', 'party']);
    expect(glyphOf('party_dissolved')).toEqual(['society', 'party']);
  });

  it('turns a position back into the nearest tick, inside the run', () => {
    expect(tickAtX(TIMELINE_PADDING, 12, 124)).toBe(0);
    expect(tickAtX(124 - TIMELINE_PADDING, 12, 124)).toBe(12);
    expect(tickAtX(-50, 12, 124)).toBe(0);
    expect(tickAtX(5000, 12, 124)).toBe(12);
    expect(tickAtX(62, 12, 124)).toBe(6);
  });
});
