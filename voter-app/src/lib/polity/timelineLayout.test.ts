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
    ]) {
      expect(glyphOf(type)[1]).not.toBe('other');
    }
  });

  it('turns a position back into the nearest tick, inside the run', () => {
    expect(tickAtX(TIMELINE_PADDING, 12, 124)).toBe(0);
    expect(tickAtX(124 - TIMELINE_PADDING, 12, 124)).toBe(12);
    expect(tickAtX(-50, 12, 124)).toBe(0);
    expect(tickAtX(5000, 12, 124)).toBe(12);
    expect(tickAtX(62, 12, 124)).toBe(6);
  });
});
