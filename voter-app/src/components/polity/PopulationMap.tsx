import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { drawScene } from '../../lib/polity/drawScene';
import { directionOf, makeHitTester, nearestInDirection } from '../../lib/polity/hitTest';
import {
  MAP_COLORS,
  buildScene,
  censusAt,
  type LegendEntry,
  type Scene,
} from '../../lib/polity/mapScene';
import { usePolityCtx } from './PolityController';
import LensSelector from './LensSelector';
import MapLegend, { legendLabel } from './MapLegend';
import PopulationTable from './PopulationTable';

// The population at the current tick (ADR-013): one canvas point per citizen,
// with parties, the president's position and pledge, the selection and the axes
// in SVG over it, on the scene's single projection. Pointing goes through a
// Delaunay search, the keyboard through the nearest point in a direction, and
// the table below gives the same reading without the canvas.

const UNMEASURED_WIDTH = 640;
const HIT_RADIUS = 8;

/** The width of the element given to the returned ref, re-observed whenever that element changes. */
function useWidth(): [(element: HTMLDivElement | null) => void, number] {
  const [element, setElement] = useState<HTMLDivElement | null>(null);
  const [width, setWidth] = useState(UNMEASURED_WIDTH);
  useLayoutEffect(() => {
    if (!element) return undefined;
    const observer = new ResizeObserver(([entry]) => {
      if (entry && entry.contentRect.width > 0) setWidth(entry.contentRect.width);
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, [element]);
  return [setElement, width];
}

const Axis: React.FC<{ scene: Scene; axis: 0 | 1; label: string; issues: string }> = ({
  scene,
  axis,
  label,
  issues,
}) =>
  axis === 0 ? (
    <text
      x={scene.width - 6}
      y={scene.height - 6}
      textAnchor="end"
      className="fill-muted-foreground text-[10px]"
    >
      {label} — {issues}
    </text>
  ) : (
    <text x={6} y={12} className="fill-muted-foreground text-[10px]">
      {label} — {issues}
    </text>
  );

const PopulationMap: React.FC = () => {
  const { t } = useTranslation('polity');
  const { overview, frame, lens, tick, citizen, setCitizen } = usePolityCtx();
  const [holder, width] = useWidth();
  const canvas = useRef<HTMLCanvasElement>(null);
  const height = Math.round(Math.min(Math.max(width * 0.6, 260), 560));

  const scene = useMemo(() => {
    if (!overview || !frame) return null;
    const census = censusAt(
      overview.projection.citizens,
      Math.floor(tick / overview.ticks_per_year)
    );
    return buildScene(
      {
        citizens: census?.xy ?? [],
        frame,
        citizenParties: overview.citizen_parties,
        parties: overview.parties,
        president: frame.president ?? null,
      },
      lens,
      width,
      height
    );
  }, [overview, frame, lens, tick, width, height]);
  const hitTest = useMemo(() => (scene ? makeHitTester(scene.points) : null), [scene]);

  useEffect(() => {
    const element = canvas.current;
    const context = element?.getContext('2d');
    if (!element || !context || !scene) return;
    const ratio = window.devicePixelRatio || 1;
    element.width = Math.round(scene.width * ratio);
    element.height = Math.round(scene.height * ratio);
    drawScene(context, scene, ratio);
  }, [scene]);

  if (!overview) return null;
  if (!scene || !hitTest) {
    // The measured element renders in every state: the size observer attaches once, at mount.
    return (
      <section data-testid="polity-map" className="rounded-md border border-border px-3 py-2">
        <div ref={holder} className="w-full">
          <p
            data-testid="polity-map-loading"
            role="status"
            className="text-sm text-muted-foreground"
          >
            {t('map.loadingFrame')}
          </p>
        </div>
      </section>
    );
  }

  const latent = overview.projection.method === 'latent';
  const issues = (axis: 0 | 1) =>
    t('map.topIssues', {
      issues: overview.projection.axes[axis]
        .map((w) => t('map.issue', { n: w.issue + 1 }))
        .join(', '),
    });
  const counts = scene.legend
    .map((entry: LegendEntry) => `${legendLabel(t, entry.key)} ${entry.count}`)
    .join(', ');
  const selected = citizen === null ? undefined : scene.points[citizen];

  const onClick = (event: React.MouseEvent<HTMLDivElement>) => {
    const box = event.currentTarget.getBoundingClientRect();
    setCitizen(hitTest(event.clientX - box.left, event.clientY - box.top, HIT_RADIUS));
  };
  const onKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'Escape') {
      event.preventDefault();
      setCitizen(null);
      return;
    }
    const direction = directionOf(event.key);
    if (!direction) return;
    event.preventDefault();
    const next = nearestInDirection(scene.points, citizen, direction, [
      scene.width / 2,
      scene.height / 2,
    ]);
    if (next !== null) setCitizen(next);
  };

  return (
    <section data-testid="polity-map" className="rounded-md border border-border px-3 py-2">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-display text-sm font-semibold">{t('map.title')}</h2>
        <LensSelector />
      </div>
      {lens === 'vote' && overview.vote_coverage !== 'all' && (
        <p data-testid="polity-map-vote-note" className="mb-1 text-xs text-muted-foreground">
          {overview.vote_coverage === 'audit_sample' ? t('map.auditNote') : t('map.noVotesNote')}
        </p>
      )}
      {overview.projection.positions === 'yearly' && (
        <p data-testid="polity-map-yearly-note" className="mb-1 text-xs text-muted-foreground">
          {t('map.yearlyNote')}
        </p>
      )}
      <div ref={holder} className="w-full">
        {/* role="application" is ARIA's role for a surface with its own keyboard model: the map
            has no DOM node per citizen, so option/grid roles do not fit (ADR-013). jsx-a11y
            counts it as non-interactive. */}
        {/* eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions */}
        <div
          data-testid="polity-map-surface"
          role="application"
          aria-roledescription={t('map.title')}
          aria-label={t('map.keys')}
          tabIndex={0}
          className="relative cursor-crosshair outline-none focus-visible:ring-2 focus-visible:ring-primary"
          style={{ width: scene.width, height: scene.height }}
          onClick={onClick}
          onKeyDown={onKeyDown}
        >
          <canvas
            ref={canvas}
            data-testid="polity-map-canvas"
            role="img"
            aria-label={t('map.summary', { tick, population: overview.population, counts })}
            style={{ width: scene.width, height: scene.height }}
            className="absolute inset-0"
          />
          <svg
            data-testid="polity-map-overlay"
            width={scene.width}
            height={scene.height}
            className="pointer-events-none absolute inset-0"
            aria-hidden="true"
          >
            <Axis
              scene={scene}
              axis={0}
              label={latent ? t('map.axisLatent1') : t('map.axisPca1')}
              issues={issues(0)}
            />
            <Axis
              scene={scene}
              axis={1}
              label={latent ? t('map.axisLatent2') : t('map.axisPca2')}
              issues={issues(1)}
            />
            {scene.parties.map((party) => (
              <g key={party.partyId} data-testid="polity-map-party">
                <title>{t('map.party', { id: party.partyId })}</title>
                <circle
                  cx={party.x}
                  cy={party.y}
                  r={9}
                  fill="none"
                  stroke={MAP_COLORS[party.color]}
                  strokeWidth={2}
                />
                <text
                  x={party.x}
                  y={party.y + 3}
                  textAnchor="middle"
                  className="text-[9px] font-semibold"
                  fill={MAP_COLORS[party.color]}
                >
                  {party.partyId}
                </text>
              </g>
            ))}
            {scene.president && (
              <g data-testid="polity-map-president">
                <title>{t('map.president', { id: scene.president.id })}</title>
                {scene.president.pledgedX !== null && scene.president.pledgedY !== null && (
                  <>
                    <line
                      data-testid="polity-map-drift"
                      x1={scene.president.pledgedX}
                      y1={scene.president.pledgedY}
                      x2={scene.president.x}
                      y2={scene.president.y}
                      stroke={MAP_COLORS.vermillion}
                      strokeDasharray="3 3"
                    />
                    <rect
                      x={scene.president.pledgedX - 4}
                      y={scene.president.pledgedY - 4}
                      width={8}
                      height={8}
                      fill="none"
                      stroke={MAP_COLORS.vermillion}
                    >
                      <title>{t('map.pledge')}</title>
                    </rect>
                  </>
                )}
                <path
                  d={`M${scene.president.x},${scene.president.y - 8} L${scene.president.x + 8},${scene.president.y} L${scene.president.x},${scene.president.y + 8} L${scene.president.x - 8},${scene.president.y} Z`}
                  fill="none"
                  stroke={MAP_COLORS.vermillion}
                  strokeWidth={2}
                />
              </g>
            )}
            {selected && (
              <circle
                data-testid="polity-map-selection"
                cx={selected.x}
                cy={selected.y}
                r={8}
                fill="none"
                className="stroke-foreground"
                strokeWidth={2}
              />
            )}
          </svg>
        </div>
      </div>
      {selected && (
        <p data-testid="polity-map-selected" className="mt-1 text-xs">
          {t('map.selected', { id: selected.id })}
        </p>
      )}
      <MapLegend entries={scene.legend} />
      <PopulationTable scene={scene} />
    </section>
  );
};

export default PopulationMap;
