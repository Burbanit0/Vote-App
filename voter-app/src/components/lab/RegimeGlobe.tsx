import React from 'react';
import { useTranslation } from 'react-i18next';
import { geoOrthographic, geoPath, geoGraticule, geoDistance } from 'd3';
import { cn } from '@/lib/utils';
import ATLAS, {
  ATLAS_METHODS,
  METHOD_COLOR,
  BLANK_COLOR,
  BLANK_UNKNOWN_COLOR,
  type AtlasEntry,
} from '../../lib/electoralAtlas';
import type { BlankVoteStatus } from '../../data/blankVoteRegimes';

const BLANK_STATUS_ORDER: BlankVoteStatus[] = [
  'competitive',
  'threshold',
  'counted_separate',
  'symbolic',
  'merged_invalid',
];

// RegimeGlobe — a rotating 3D orthographic globe (d3-geo, no new dependency, no
// country polygons) plotting each democracy as a dot, coloured by its electoral
// method or by its blank-vote regime. Auto-spins (respecting reduced-motion),
// drag to turn, click a dot for the country card. Doubles as the app's animation
// demo. Rotation lives in a ref; a tick state drives the re-render so the rAF
// loop never reads a stale closure.

const SIZE = 320;
const R = 150;
const C = SIZE / 2;
const SPIN_DEG_PER_SEC = 8;

type Lens = 'method' | 'blank';

// True when we should NOT auto-spin: the user asked for reduced motion, or there
// is no matchMedia to ask (jsdom / SSR) — in which case we stay static.
const prefersReducedMotion = () =>
  typeof window === 'undefined' ||
  typeof window.matchMedia !== 'function' ||
  window.matchMedia('(prefers-reduced-motion: reduce)').matches;

const colorFor = (e: AtlasEntry, lens: Lens): string =>
  lens === 'method'
    ? METHOD_COLOR[e.method]
    : e.blankStatus
      ? BLANK_COLOR[e.blankStatus]
      : BLANK_UNKNOWN_COLOR;

const RegimeGlobe: React.FC = () => {
  const { t } = useTranslation('playground');
  const [lens, setLens] = React.useState<Lens>('method');
  const [selected, setSelected] = React.useState<AtlasEntry | null>(null);
  const [, setTick] = React.useState(0);

  const rot = React.useRef({ lambda: 0, phi: -12 });
  const dragging = React.useRef<{ x: number; y: number } | null>(null);
  const reduced = React.useRef(prefersReducedMotion());

  // Auto-rotation loop (paused while dragging; skipped under reduced-motion).
  React.useEffect(() => {
    if (reduced.current) return;
    let raf = 0;
    let last = performance.now();
    const step = (now: number) => {
      const dt = (now - last) / 1000;
      last = now;
      if (!dragging.current) {
        rot.current.lambda = (rot.current.lambda + dt * SPIN_DEG_PER_SEC) % 360;
        setTick((k) => k + 1);
      }
      raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, []);

  const onPointerDown = (e: React.PointerEvent) => {
    dragging.current = { x: e.clientX, y: e.clientY };
    (e.target as Element).setPointerCapture?.(e.pointerId);
  };
  const onPointerMove = (e: React.PointerEvent) => {
    const d = dragging.current;
    if (!d) return;
    rot.current.lambda = (rot.current.lambda + (e.clientX - d.x) * 0.5) % 360;
    rot.current.phi = Math.max(-89, Math.min(89, rot.current.phi - (e.clientY - d.y) * 0.5));
    dragging.current = { x: e.clientX, y: e.clientY };
    setTick((k) => k + 1);
    // If reduced-motion killed the loop, dragging still updates via setTick.
  };
  const endDrag = () => {
    dragging.current = null;
  };

  const { lambda, phi } = rot.current;
  const proj = geoOrthographic().scale(R).translate([C, C]).rotate([lambda, phi]);
  const path = geoPath(proj);
  const center: [number, number] = [-lambda, -phi];

  const legend =
    lens === 'method'
      ? ATLAS_METHODS.map((m) => ({
          key: m,
          color: METHOD_COLOR[m],
          label: t(`atlas.method.${m}`),
        }))
      : [
          ...BLANK_STATUS_ORDER.map((s) => ({
            key: s,
            color: BLANK_COLOR[s],
            label: t(`blankVote.status.${s}`),
          })),
          { key: 'unknown', color: BLANK_UNKNOWN_COLOR, label: t('atlas.unknownBlank') },
        ];

  return (
    <div data-testid="regime-globe" className="flex flex-col gap-3">
      <div>
        <p className="font-mono text-[0.62rem] uppercase tracking-[0.2em] text-primary">
          {t('atlas.kicker')}
        </p>
        <h2 className="font-display text-lg font-bold tracking-tight">{t('atlas.title')}</h2>
        <p className="mt-0.5 max-w-2xl text-sm text-muted-foreground">{t('atlas.intro')}</p>
      </div>

      {/* Colour-lens toggle */}
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="text-muted-foreground">{t('atlas.colorBy')}</span>
        {(['method', 'blank'] as const).map((l) => (
          <button
            key={l}
            type="button"
            data-testid={`atlas-lens-${l}`}
            aria-pressed={lens === l}
            onClick={() => setLens(l)}
            className={cn(
              'rounded-md border px-2 py-0.5',
              lens === l
                ? 'border-primary bg-primary/10 text-primary'
                : 'border-border text-muted-foreground hover:border-primary/40'
            )}
          >
            {l === 'method' ? t('atlas.byMethod') : t('atlas.byBlank')}
          </button>
        ))}
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-start">
        <svg
          viewBox={`0 0 ${SIZE} ${SIZE}`}
          className="w-full max-w-[320px] shrink-0 cursor-grab touch-none select-none active:cursor-grabbing"
          role="img"
          aria-label={t('atlas.title')}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={endDrag}
          onPointerLeave={endDrag}
        >
          {/* Ocean sphere + graticule */}
          <path d={path({ type: 'Sphere' }) ?? ''} fill="rgba(56,132,255,0.10)" stroke="none" />
          <path
            d={path(geoGraticule()()) ?? ''}
            fill="none"
            stroke="rgba(120,120,120,0.28)"
            strokeWidth={0.5}
          />
          <path
            d={path({ type: 'Sphere' }) ?? ''}
            fill="none"
            stroke="rgba(120,120,120,0.45)"
            strokeWidth={1}
          />
          {/* Regime dots (front hemisphere only) */}
          {ATLAS.map((e) => {
            if (geoDistance([e.lon, e.lat], center) > Math.PI / 2) return null;
            const xy = proj([e.lon, e.lat]);
            if (!xy) return null;
            const isSel = selected?.country === e.country;
            return (
              <circle
                key={e.country}
                data-testid={`atlas-dot-${e.country}`}
                cx={xy[0]}
                cy={xy[1]}
                r={isSel ? 7 : 4.5}
                fill={colorFor(e, lens)}
                stroke="#fff"
                strokeWidth={isSel ? 2 : 1}
                className="cursor-pointer"
                onPointerDown={(ev) => ev.stopPropagation()}
                onClick={() => setSelected(e)}
              >
                <title>{e.country}</title>
              </circle>
            );
          })}
        </svg>

        <div className="flex min-w-0 flex-1 flex-col gap-3">
          {/* Selected country card */}
          {selected ? (
            <div
              data-testid="atlas-card"
              className="rounded-lg border border-border bg-card p-3 text-sm"
            >
              <p className="font-semibold">
                <span aria-hidden className="mr-1.5">
                  {selected.flag}
                </span>
                {selected.country}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                {t('atlas.methodLabel')}{' '}
                <span className="font-medium text-foreground">
                  {t(`atlas.method.${selected.method}`)}
                </span>
              </p>
              <p className="text-xs text-muted-foreground">
                {t('atlas.blankLabel')}{' '}
                <span className="font-medium text-foreground">
                  {selected.blankStatus
                    ? t(`blankVote.status.${selected.blankStatus}`)
                    : t('atlas.unknownBlank')}
                </span>
              </p>
              <p className="mt-1 text-[0.65rem] text-muted-foreground/80">{selected.source}</p>
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">{t('atlas.dragHint')}</p>
          )}

          {/* Legend */}
          <ul className="flex flex-col gap-1 text-xs">
            {legend.map((l) => (
              <li key={l.key} className="flex items-center gap-1.5">
                <span
                  aria-hidden
                  className="h-2.5 w-2.5 shrink-0 rounded-full"
                  style={{ background: l.color }}
                />
                <span className="text-muted-foreground">{l.label}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <p className="text-[0.68rem] text-muted-foreground/80">{t('atlas.source')}</p>
    </div>
  );
};

export default RegimeGlobe;
