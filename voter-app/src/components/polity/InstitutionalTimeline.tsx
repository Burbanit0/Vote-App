import React, { useCallback, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useWidth } from '../../hooks/useWidth';
import {
  LANE_HEIGHT,
  TIMELINE_LANES,
  glyphOf,
  layoutTimeline,
  tickAtX,
  type Glyph,
  type TimelineLane,
} from '../../lib/polity/timelineLayout';
import { usePolityCtx } from './PolityController';

// The run's institutional story on one axis of ticks, in native SVG (ADR-005):
// term bands on the presidency lane, glyphs for elections, checks, legislature
// and society, and a playhead at the current tick. A click moves the player.

const UNMEASURED_WIDTH = 800;
/** Below this many pixels a tick, a long run's glyphs merge into bars: the lanes scroll instead. */
const MIN_TICK_WIDTH = 8;
const BAND_CLASSES = ['fill-primary/25', 'fill-primary/45'];
const VACANCY_CLASS = 'fill-none stroke-muted-foreground';

const LANE_KEYS: Record<TimelineLane, string> = {
  presidency: 'timeline.lanePresidency',
  elections: 'timeline.laneElections',
  accountability: 'timeline.laneAccountability',
  legislature: 'timeline.laneLegislature',
  constitution: 'timeline.laneConstitution',
  society: 'timeline.laneSociety',
};

const ENDED_KEYS: Record<string, string> = {
  election: 'timeline.endedElection',
  legitimacy_floor: 'timeline.endedRecall',
  confidence_vote: 'timeline.endedConfidence',
  run_end: 'timeline.endedRunEnd',
};

/** The legend: one entry per shape, in lane order. Kinds drawn alike share an entry. */
const LEGEND = [
  ['elected', ['elected']],
  ['noWinner', ['noWinner', 'invalidated']],
  ['snap', ['snap']],
  ['campaign', ['campaign']],
  ['recall', ['recall']],
  ['petition', ['confidence', 'petition']],
  ['extraLegal', ['extraLegal']],
  ['bill', ['legislative', 'bill', 'coalition']],
  ['amended', ['amended']],
  ['amendment', ['amendment']],
  ['party', ['party']],
  ['other', ['scandal', 'shock', 'rotation', 'other']],
] as const;

const diamond = (x: number, y: number) =>
  `M${x},${y - 5} L${x + 5},${y} L${x},${y + 5} L${x - 5},${y} Z`;

/** One shape per glyph kind, so a glyph reads without its colour. */
const GlyphShape: React.FC<{ glyph: Pick<Glyph, 'x' | 'y' | 'kind'> }> = ({ glyph }) => {
  const { x, y, kind } = glyph;
  switch (kind) {
    case 'elected':
      return <circle cx={x} cy={y} r={4} className="fill-primary" />;
    case 'noWinner':
    case 'invalidated':
      return (
        <circle cx={x} cy={y} r={4} className="fill-background stroke-primary" strokeWidth={1.5} />
      );
    case 'snap':
      return (
        <path
          d={`M${x},${y - 5} L${x + 5},${y + 4} L${x - 5},${y + 4} Z`}
          className="fill-amber-600"
        />
      );
    case 'recall':
      return (
        <path
          d={`M${x - 4},${y - 4} L${x + 4},${y + 4} M${x + 4},${y - 4} L${x - 4},${y + 4}`}
          className="stroke-red-700"
          strokeWidth={2}
        />
      );
    case 'confidence':
    case 'petition':
      return <path d={diamond(x, y)} className="fill-orange-500" />;
    case 'legislative':
    case 'bill':
    case 'coalition':
      return <rect x={x - 4} y={y - 4} width={8} height={8} className="fill-sky-700" />;
    case 'amended':
      return <circle cx={x} cy={y} r={4.5} className="fill-violet-700" />;
    case 'amendment':
      return (
        <path d={diamond(x, y)} className="fill-background stroke-violet-700" strokeWidth={1.5} />
      );
    case 'extraLegal':
      // A downward triangle: the reverse of an election's mark, for an office kept against the rules.
      return (
        <path
          d={`M${x},${y + 5} L${x + 5},${y - 4} L${x - 5},${y - 4} Z`}
          className="fill-red-700"
        />
      );
    case 'campaign':
      return (
        <path
          d={`M${x - 4},${y} L${x + 4},${y} M${x},${y - 4} L${x},${y + 4}`}
          className="stroke-emerald-700"
          strokeWidth={2}
        />
      );
    case 'party':
      // An outlined square: a party is the frame citizens gather in, not yet seats (a filled square).
      return (
        <rect
          x={x - 4}
          y={y - 4}
          width={8}
          height={8}
          className="fill-background stroke-indigo-700"
          strokeWidth={1.5}
        />
      );
    default:
      return <rect x={x - 1} y={y - 5} width={2} height={10} className="fill-muted-foreground" />;
  }
};

const InstitutionalTimeline: React.FC = () => {
  const { t } = useTranslation('polity');
  const { overview, tick, setTick } = usePolityCtx();
  const [measure, width] = useWidth(UNMEASURED_WIDTH);
  const scroller = useRef<HTMLDivElement | null>(null);
  const holder = useCallback(
    (element: HTMLDivElement | null) => {
      measure(element);
      scroller.current = element;
    },
    [measure]
  );
  const lastTick = overview?.last_tick ?? 0;
  const svgWidth = Math.max(width, (lastTick + 1) * MIN_TICK_WIDTH);
  const geometry = overview
    ? layoutTimeline(overview.terms, overview.timeline, lastTick, svgWidth)
    : null;
  const playheadX = geometry?.tickX(tick);

  // When the lanes scroll, playback and jumps bring the playhead back into view.
  useEffect(() => {
    const element = scroller.current;
    if (!element || playheadX === undefined) return;
    if (playheadX < element.scrollLeft || playheadX > element.scrollLeft + element.clientWidth) {
      element.scrollLeft = playheadX - element.clientWidth / 2;
    }
  }, [playheadX]);

  if (!overview || !geometry) return null;

  const eventName = (type: string) => t(`timeline.eventNames.${type}`, { defaultValue: type });
  const drawn = new Set(geometry.glyphs.map((glyph) => glyph.kind));
  const onClick = (event: React.MouseEvent<SVGSVGElement>) => {
    const box = event.currentTarget.getBoundingClientRect();
    setTick(tickAtX(event.clientX - box.left, lastTick, svgWidth));
  };

  return (
    <section data-testid="polity-timeline" className="rounded-md border border-border px-3 py-2">
      <h2 className="mb-1 font-display text-sm font-semibold">{t('timeline.title')}</h2>
      <div className="flex gap-2">
        <ul
          className="shrink-0 pt-3 text-right text-[0.66rem] text-muted-foreground"
          aria-hidden="true"
        >
          {TIMELINE_LANES.map((lane) => (
            <li key={lane} style={{ height: LANE_HEIGHT, lineHeight: `${LANE_HEIGHT}px` }}>
              {t(LANE_KEYS[lane])}
            </li>
          ))}
        </ul>
        <div ref={holder} className="min-w-0 flex-1 overflow-x-auto">
          <svg
            data-testid="timeline-svg"
            role="img"
            aria-label={t('timeline.summary', {
              terms: overview.terms.length,
              events: overview.timeline.length,
              ticks: lastTick + 1,
            })}
            width={svgWidth}
            height={geometry.height}
            className="block cursor-pointer"
            onClick={onClick}
          >
            {geometry.bands.map((band, i) => (
              <rect
                key={`${band.holder}-${band.startTick}`}
                data-testid="timeline-term"
                x={band.x}
                y={geometry.laneY.presidency - 7}
                width={band.width}
                height={14}
                rx={2}
                className={BAND_CLASSES[i % BAND_CLASSES.length]}
              >
                <title>
                  {t('timeline.term', {
                    holder: band.holder,
                    start: band.startTick,
                    end: t(ENDED_KEYS[band.endedBy] ?? 'timeline.endedElection'),
                  })}
                </title>
              </rect>
            ))}
            {geometry.vacancies.map((vacancy) => (
              <rect
                key={vacancy.startTick}
                data-testid="timeline-vacancy"
                x={vacancy.x}
                y={geometry.laneY.presidency - 7}
                width={vacancy.width}
                height={14}
                rx={2}
                className={VACANCY_CLASS}
                strokeDasharray="3 2"
              >
                <title>
                  {t('timeline.vacancy', { start: vacancy.startTick, end: vacancy.endTick })}
                </title>
              </rect>
            ))}
            {geometry.glyphs.map((glyph, i) => (
              <g key={i} data-testid="timeline-glyph" data-kind={glyph.kind} data-tick={glyph.tick}>
                <title>
                  {t('timeline.jump', { tick: glyph.tick, event: eventName(glyph.eventType) })}
                </title>
                <GlyphShape glyph={glyph} />
              </g>
            ))}
            <line
              data-testid="timeline-playhead"
              x1={geometry.tickX(tick)}
              x2={geometry.tickX(tick)}
              y1={0}
              y2={geometry.height}
              className="stroke-foreground"
              strokeWidth={1.5}
            />
          </svg>
        </div>
      </div>
      <ul
        data-testid="timeline-legend"
        aria-label={t('timeline.legendLabel')}
        className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs"
      >
        {geometry.vacancies.length > 0 && (
          <li data-testid="timeline-legend-vacancy" className="flex items-center gap-1.5">
            <svg width={16} height={12} aria-hidden="true" className="shrink-0">
              <rect
                x={1}
                y={2}
                width={14}
                height={8}
                rx={2}
                className={VACANCY_CLASS}
                strokeDasharray="3 2"
              />
            </svg>
            {t('timeline.legend.vacancy')}
          </li>
        )}
        {LEGEND.filter(([, kinds]) => kinds.some((kind) => drawn.has(kind))).map(([key, kinds]) => (
          <li
            key={key}
            data-testid={`timeline-legend-${key}`}
            className="flex items-center gap-1.5"
          >
            <svg width={12} height={12} aria-hidden="true" className="shrink-0">
              <GlyphShape glyph={{ x: 6, y: 6, kind: kinds[0] }} />
            </svg>
            {t(`timeline.legend.${key}`)}
          </li>
        ))}
      </ul>
      <details className="mt-1 text-xs">
        <summary className="cursor-pointer text-muted-foreground">
          {t('timeline.eventList')}
        </summary>
        {/* By lane, each folded under its count: a long run has a hundred events and more. */}
        {TIMELINE_LANES.map((lane) => {
          const entries = overview.timeline.filter(
            (entry) => glyphOf(entry.event_type)[0] === lane
          );
          return (
            entries.length > 0 && (
              <details key={lane} data-testid={`timeline-events-${lane}`} className="ml-3 mt-1">
                <summary className="cursor-pointer">
                  {t(LANE_KEYS[lane])}{' '}
                  <span className="text-muted-foreground">{entries.length}</span>
                </summary>
                <ol className="mt-1 flex flex-wrap gap-1">
                  {entries.map((entry, i) => (
                    <li key={i}>
                      <button
                        type="button"
                        data-testid="timeline-event-jump"
                        data-tick={entry.tick}
                        data-event={entry.event_type}
                        className="rounded border border-border px-1.5 py-0.5"
                        onClick={() => setTick(entry.tick)}
                      >
                        {t('timeline.jump', {
                          tick: entry.tick,
                          event: eventName(entry.event_type),
                        })}
                      </button>
                    </li>
                  ))}
                </ol>
              </details>
            )
          );
        })}
      </details>
    </section>
  );
};

export default InstitutionalTimeline;
