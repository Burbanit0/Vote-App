import React, { useLayoutEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  LANE_HEIGHT,
  TIMELINE_LANES,
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
const BAND_CLASSES = ['fill-primary/25', 'fill-primary/45'];

const LANE_KEYS: Record<TimelineLane, string> = {
  presidency: 'timeline.lanePresidency',
  elections: 'timeline.laneElections',
  accountability: 'timeline.laneAccountability',
  legislature: 'timeline.laneLegislature',
  society: 'timeline.laneSociety',
};

const ENDED_KEYS: Record<string, string> = {
  election: 'timeline.endedElection',
  legitimacy_floor: 'timeline.endedRecall',
  confidence_vote: 'timeline.endedConfidence',
  run_end: 'timeline.endedRunEnd',
};

/** One shape per glyph kind, so a glyph reads without its colour. */
const GlyphShape: React.FC<{ glyph: Glyph }> = ({ glyph }) => {
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
      return (
        <path
          d={`M${x},${y - 5} L${x + 5},${y} L${x},${y + 5} L${x - 5},${y} Z`}
          className="fill-orange-500"
        />
      );
    case 'legislative':
    case 'bill':
    case 'coalition':
      return <rect x={x - 4} y={y - 4} width={8} height={8} className="fill-sky-700" />;
    default:
      return <rect x={x - 1} y={y - 5} width={2} height={10} className="fill-muted-foreground" />;
  }
};

const InstitutionalTimeline: React.FC = () => {
  const { t } = useTranslation('polity');
  const { overview, tick, setTick } = usePolityCtx();
  const holder = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(UNMEASURED_WIDTH);

  useLayoutEffect(() => {
    const element = holder.current;
    if (!element) return undefined;
    const observer = new ResizeObserver(([entry]) => {
      if (entry && entry.contentRect.width > 0) setWidth(entry.contentRect.width);
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  if (!overview) return null;

  const lastTick = overview.last_tick;
  const geometry = layoutTimeline(overview.terms, overview.timeline, lastTick, width);
  const eventName = (type: string) => t(`timeline.eventNames.${type}`, { defaultValue: type });
  const onClick = (event: React.MouseEvent<SVGSVGElement>) => {
    const box = event.currentTarget.getBoundingClientRect();
    setTick(tickAtX(event.clientX - box.left, lastTick, width));
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
        <div ref={holder} className="min-w-0 flex-1">
          <svg
            data-testid="timeline-svg"
            role="img"
            aria-label={t('timeline.summary', {
              terms: overview.terms.length,
              events: overview.timeline.length,
              ticks: lastTick + 1,
            })}
            width={width}
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
      <details className="mt-1 text-xs">
        <summary className="cursor-pointer text-muted-foreground">
          {t('timeline.eventList')}
        </summary>
        <ol className="mt-1 flex flex-wrap gap-1">
          {overview.timeline.map((entry, i) => (
            <li key={i}>
              <button
                type="button"
                data-testid="timeline-event-jump"
                data-tick={entry.tick}
                data-event={entry.event_type}
                className="rounded border border-border px-1.5 py-0.5"
                onClick={() => setTick(entry.tick)}
              >
                {t('timeline.jump', { tick: entry.tick, event: eventName(entry.event_type) })}
              </button>
            </li>
          ))}
        </ol>
      </details>
    </section>
  );
};

export default InstitutionalTimeline;
