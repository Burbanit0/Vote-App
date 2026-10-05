/**
 * lib/polity/timelineLayout.ts — the institutional timeline's geometry, pure.
 *
 * One horizontal axis of ticks. The presidency lane carries each term as a band
 * (ended by an election, a recall or the run's end); the other lanes carry the
 * institutional events as glyphs, sorted by what they are about. Events on the
 * same tick and lane stack a few pixels apart instead of hiding one another.
 */

export const TIMELINE_LANES = [
  'presidency',
  'elections',
  'accountability',
  'legislature',
  'constitution',
  'society',
] as const;
export type TimelineLane = (typeof TIMELINE_LANES)[number];

/** What a glyph shows, from its event type. */
export type GlyphKind =
  | 'elected'
  | 'noWinner'
  | 'invalidated'
  | 'snap'
  | 'legislative'
  | 'recall'
  | 'confidence'
  | 'petition'
  | 'bill'
  | 'coalition'
  | 'scandal'
  | 'shock'
  | 'rotation'
  | 'amended'
  | 'amendment'
  | 'extraLegal'
  | 'campaign'
  | 'party'
  | 'other';

const GLYPHS: Record<string, [TimelineLane, GlyphKind]> = {
  elected: ['elections', 'elected'],
  election_no_winner: ['elections', 'noWinner'],
  election_invalidated: ['elections', 'invalidated'],
  snap_election_triggered: ['elections', 'snap'],
  legislative_result: ['elections', 'legislative'],
  recalled: ['accountability', 'recall'],
  confidence_vote_triggered: ['accountability', 'confidence'],
  confidence_vote_result: ['accountability', 'confidence'],
  petition_launched: ['accountability', 'petition'],
  petition_expired: ['accountability', 'petition'],
  bill_proposed: ['legislature', 'bill'],
  bill_enacted: ['legislature', 'bill'],
  bill_blocked: ['legislature', 'bill'],
  coalition_formed: ['legislature', 'coalition'],
  coalition_failed: ['legislature', 'coalition'],
  scandal_occurred: ['society', 'scandal'],
  economic_shock_tick: ['society', 'shock'],
  sortition_rotation: ['society', 'rotation'],
  constitution_amended: ['constitution', 'amended'],
  amendment_proposed: ['constitution', 'amendment'],
  amendment_resolved: ['constitution', 'amendment'],
  referendum_held: ['constitution', 'amendment'],
  // Phase 5 (ADR-022, ADR-023). Both are institutional, so they reached the timeline before they
  // had glyphs -- as anonymous 'other' marks in the society lane. An extra-legal act answers to
  // accountability (it is the opposite of a recall); a campaign belongs to the election it precedes.
  extra_legal_act: ['accountability', 'extraLegal'],
  campaign_run: ['elections', 'campaign'],
  // Phase 4 (ADR-018): both are institutional, so they reached the timeline from the start --
  // as the society lane's generic 'other' bar, lumped with scandals and rotations. Founding and
  // dissolving share a shape, as a bill's proposal and enactment do; the event list tells them apart.
  party_founded: ['society', 'party'],
  party_dissolved: ['society', 'party'],
};

export interface TermInput {
  holder: number;
  start_tick: number;
  end_tick: number;
  ended_by: string;
}

export interface EventInput {
  tick: number;
  event_type: string;
  citizen_id?: number | null;
}

interface Band {
  holder: number;
  x: number;
  width: number;
  endedBy: string;
  startTick: number;
}

/** Ticks no term covers: nobody held the presidency, from `startTick` until `endTick`. */
interface Vacancy {
  x: number;
  width: number;
  startTick: number;
  endTick: number;
}

export interface Glyph {
  x: number;
  y: number;
  lane: TimelineLane;
  kind: GlyphKind;
  tick: number;
  eventType: string;
  citizenId: number | null;
}

export interface TimelineGeometry {
  width: number;
  height: number;
  laneY: Record<TimelineLane, number>;
  bands: Band[];
  vacancies: Vacancy[];
  glyphs: Glyph[];
  tickX: (tick: number) => number;
}

export const LANE_HEIGHT = 22;
export const TIMELINE_PADDING = 12;
const STACK_OFFSET = 5;
/** How far below its lane's centre a stacked glyph may sit and still stay inside the lane: half a
 * lane, less a glyph's own half-height. Unbounded, a stack of campaigns (one per nominee, so five to
 * ten on an election tick) spilled down through the lanes beneath and hid their glyphs. */
const MAX_STACK_DROP = LANE_HEIGHT / 2 - 5;
const MIN_BAND_WIDTH = 2;

export function glyphOf(eventType: string): [TimelineLane, GlyphKind] {
  return GLYPHS[eventType] ?? ['society', 'other'];
}

export function layoutTimeline(
  terms: readonly TermInput[],
  events: readonly EventInput[],
  lastTick: number,
  width: number
): TimelineGeometry {
  const span = Math.max(lastTick, 1);
  const inner = Math.max(width - 2 * TIMELINE_PADDING, 1);
  const tickX = (tick: number) => TIMELINE_PADDING + (tick / span) * inner;
  const laneY = Object.fromEntries(
    TIMELINE_LANES.map((lane, i) => [lane, TIMELINE_PADDING + i * LANE_HEIGHT + LANE_HEIGHT / 2])
  ) as Record<TimelineLane, number>;

  const bands = terms.map((term) => ({
    holder: term.holder,
    x: tickX(term.start_tick),
    // A term that ran to the end of the run covers its last tick as well.
    width: Math.max(
      tickX(
        term.ended_by === 'run_end' ? Math.max(term.end_tick, term.start_tick) : term.end_tick
      ) - tickX(term.start_tick),
      MIN_BAND_WIDTH
    ),
    endedBy: term.ended_by,
    startTick: term.start_tick,
  }));

  // A recall empties the office until the next election: those ticks belong to no term.
  const vacancies: Vacancy[] = [];
  const vacant = (from: number, to: number) => {
    if (to > from) {
      vacancies.push({
        x: tickX(from),
        width: tickX(to) - tickX(from),
        startTick: from,
        endTick: to,
      });
    }
  };
  let covered = 0;
  for (const term of [...terms].sort((a, b) => a.start_tick - b.start_tick)) {
    vacant(covered, term.start_tick);
    covered = Math.max(covered, term.end_tick);
  }
  vacant(covered, lastTick);

  const slotOf = (event: EventInput) => `${glyphOf(event.event_type)[0]}:${event.tick}`;
  const slotSize = new Map<string, number>();
  for (const event of events) slotSize.set(slotOf(event), (slotSize.get(slotOf(event)) ?? 0) + 1);

  const stacked = new Map<string, number>();
  const glyphs = events.map((event) => {
    const [lane, kind] = glyphOf(event.event_type);
    const slot = slotOf(event);
    const depth = stacked.get(slot) ?? 0;
    stacked.set(slot, depth + 1);
    // A short stack keeps its 5px spacing; a long one tightens so it never leaves its lane.
    const size = slotSize.get(slot) ?? 1;
    const step = size > 1 ? Math.min(STACK_OFFSET, MAX_STACK_DROP / (size - 1)) : 0;
    return {
      x: tickX(event.tick),
      y: laneY[lane] + depth * step,
      lane,
      kind,
      tick: event.tick,
      eventType: event.event_type,
      citizenId: event.citizen_id ?? null,
    };
  });

  return {
    width,
    height: 2 * TIMELINE_PADDING + TIMELINE_LANES.length * LANE_HEIGHT,
    laneY,
    bands,
    vacancies,
    glyphs,
    tickX,
  };
}

/** The tick under a horizontal position on the timeline (clicks and drags). */
export function tickAtX(x: number, lastTick: number, width: number): number {
  const inner = Math.max(width - 2 * TIMELINE_PADDING, 1);
  const tick = Math.round(((x - TIMELINE_PADDING) / inner) * Math.max(lastTick, 1));
  return Math.min(Math.max(tick, 0), Math.max(lastTick, 0));
}
