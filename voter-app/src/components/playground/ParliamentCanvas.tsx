import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { buildVoronoiPaths } from '../../utils/voronoiRegions';
import { cn } from '@/lib/utils';
import type { NamedPt, Pt } from '../../lib/playgroundVoting';
import type { AssemblyResult } from '../../services/assemblyApi';

// ParliamentCanvas (Lab reshape P3) — the live party-level viz. Parties are
// draggable on the ideology map (voters re-attach to their nearest party
// instantly); the hemicycle, the votes→seats bars and the coalition builder
// reflow from the backend /assembly result (debounced by the page).
//
// NB the map's voter cloud is the frontend's deterministic sample (same ideology
// presets/seed family as the backend) — it is the *control surface*; all precise
// numbers (seats, Gallagher, ENP, wasted votes) come from the backend result.

const SVG = 480;
const MARGIN = 28;
const PLOT = SVG - 2 * MARGIN;

export const PARTY_PALETTE = [
  '#2563eb',
  '#dc2626',
  '#16a34a',
  '#9333ea',
  '#ea580c',
  '#0891b2',
  '#ca8a04',
  '#db2777',
];

const toSvg = (v: number, axis: 'x' | 'y'): number =>
  axis === 'x' ? MARGIN + ((v + 1) / 2) * PLOT : MARGIN + ((1 - v) / 2) * PLOT;

function svgToDomain(clientX: number, clientY: number, rect: DOMRect) {
  const sx = ((clientX - rect.left) / rect.width) * SVG;
  const sy = ((clientY - rect.top) / rect.height) * SVG;
  return {
    x: Math.max(-1, Math.min(1, ((sx - MARGIN) / PLOT) * 2 - 1)),
    y: Math.max(-1, Math.min(1, 1 - ((sy - MARGIN) / PLOT) * 2)),
  };
}

// ── Hemicycle geometry ────────────────────────────────────────────────────────

export interface Seat {
  x: number;
  y: number;
  party: number; // palette/party index, -1 = unassigned
}

/**
 * Lay out `total` seats in concentric half-rings and assign them to parties in
 * left→right ideological order (party order = ascending x), filling by angle —
 * the classic parliament chart.
 */
export function hemicycleSeats(
  total: number,
  partySeats: { idx: number; seats: number; x: number }[],
  width: number,
  height: number
): Seat[] {
  if (total <= 0) return [];
  const cx = width / 2;
  const cy = height - 8;
  const rMin = Math.min(width, height) * 0.35;
  const rMax = Math.min(width / 2, height) - 14;
  // Rows: enough so each row's arc fits its share with sensible spacing.
  const rows = Math.max(2, Math.ceil(Math.sqrt(total / 4)));
  const radii = Array.from({ length: rows }, (_, i) =>
    rows === 1 ? rMin : rMin + ((rMax - rMin) * i) / (rows - 1)
  );
  const weight = radii.reduce((s, r) => s + r, 0);
  // Seats per row ∝ radius, fixing rounding drift on the last row.
  const perRow = radii.map((r) => Math.round((total * r) / weight));
  let drift = total - perRow.reduce((s, n) => s + n, 0);
  for (let i = 0; drift !== 0 && i < perRow.length; i++) {
    perRow[i] += Math.sign(drift);
    drift -= Math.sign(drift);
  }
  // Generate positions with their angle, then sort left→right (angle π→0).
  const pos: { x: number; y: number; angle: number }[] = [];
  perRow.forEach((n, row) => {
    for (let k = 0; k < n; k++) {
      const angle = n === 1 ? Math.PI / 2 : Math.PI - (Math.PI * k) / (n - 1);
      pos.push({
        x: cx + radii[row] * Math.cos(angle),
        y: cy - radii[row] * Math.sin(angle),
        angle,
      });
    }
  });
  pos.sort((a, b) => b.angle - a.angle);
  // Assign blocks: parties ordered left→right by ideological x.
  const order = [...partySeats].sort((a, b) => a.x - b.x);
  const seats: Seat[] = pos.map((p) => ({ x: p.x, y: p.y, party: -1 }));
  let i = 0;
  for (const p of order) {
    for (let k = 0; k < p.seats && i < seats.length; k++, i++) {
      seats[i].party = p.idx;
    }
  }
  return seats;
}

// ── Component ─────────────────────────────────────────────────────────────────

export interface ParliamentCanvasProps {
  parties: NamedPt[];
  voters: Pt[];
  result: AssemblyResult | null;
  loading: boolean;
  /** Nominal seat count, for the grey default hemicycle before a result lands. */
  nominalSeats?: number;
  onMoveParty: (index: number, x: number, y: number) => void;
}

const ParliamentCanvas: React.FC<ParliamentCanvasProps> = ({
  parties,
  voters,
  result,
  loading,
  nominalSeats = 100,
  onMoveParty,
}) => {
  const { t } = useTranslation('playground');
  const svgRef = useRef<SVGSVGElement>(null);
  const draggingIdx = useRef<number | null>(null);
  const [coalition, setCoalition] = useState<Set<string>>(new Set());

  // Unified mouse + touch drag (same self-contained pattern as LeaderCanvas).
  useEffect(() => {
    const move = (clientX: number, clientY: number) => {
      if (draggingIdx.current === null || !svgRef.current) return;
      const { x, y } = svgToDomain(clientX, clientY, svgRef.current.getBoundingClientRect());
      onMoveParty(draggingIdx.current, x, y);
    };
    const onMM = (e: MouseEvent) => move(e.clientX, e.clientY);
    const onUp = () => {
      draggingIdx.current = null;
    };
    const onTM = (e: TouchEvent) => {
      if (draggingIdx.current === null || !e.touches[0]) return;
      e.preventDefault();
      move(e.touches[0].clientX, e.touches[0].clientY);
    };
    const svg = svgRef.current;
    window.addEventListener('mousemove', onMM);
    window.addEventListener('mouseup', onUp);
    svg?.addEventListener('touchmove', onTM, { passive: false });
    svg?.addEventListener('touchend', onUp);
    return () => {
      window.removeEventListener('mousemove', onMM);
      window.removeEventListener('mouseup', onUp);
      svg?.removeEventListener('touchmove', onTM);
      svg?.removeEventListener('touchend', onUp);
    };
  }, [onMoveParty]);

  // Party territories + instant voter re-attachment (local, live during drag).
  const territories = useMemo(() => buildVoronoiPaths(parties, SVG, SVG, toSvg, MARGIN), [parties]);
  const nearestParty = useMemo(
    () =>
      voters.map((v) => {
        let best = 0;
        let bd = Infinity;
        parties.forEach((p, i) => {
          const d = (v.x - p.x) ** 2 + (v.y - p.y) ** 2;
          if (d < bd) {
            bd = d;
            best = i;
          }
        });
        return best;
      }),
    [voters, parties]
  );

  // Hemicycle from the backend result (party colours follow the parties prop
  // order). Before a result lands, a GREY default arc shows the structure with
  // no party influence (empty partySeats → every seat unassigned → grey).
  const seats = useMemo(() => {
    if (!result) {
      return hemicycleSeats(Math.max(10, nominalSeats), [], SVG, 250);
    }
    const partySeats = result.parties.map((p) => ({
      idx: parties.findIndex((q) => q.name === p.name),
      seats: p.seats,
      x: p.x,
    }));
    return hemicycleSeats(result.assembly_size, partySeats, SVG, 250);
  }, [result, parties, nominalSeats]);

  const colorOf = (idx: number): string =>
    idx >= 0 ? PARTY_PALETTE[idx % PARTY_PALETTE.length] : '#9ca3af';

  const toggleCoalition = (name: string) => {
    setCoalition((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const coalitionSeats = result
    ? result.parties.filter((p) => coalition.has(p.name)).reduce((s, p) => s + p.seats, 0)
    : 0;
  const coalitionSpan = useMemo(() => {
    const members = parties.filter((p) => coalition.has(p.name));
    let span = 0;
    for (let i = 0; i < members.length; i++) {
      for (let j = i + 1; j < members.length; j++) {
        span = Math.max(span, Math.hypot(members[i].x - members[j].x, members[i].y - members[j].y));
      }
    }
    return span;
  }, [parties, coalition]);

  return (
    <div data-testid="canvas-parliament" className="flex flex-col gap-3">
      {/* Make a failed/absent assembly result explicit instead of silently
          hiding the hemicycle (e.g. if the backend is out of date). */}
      {!result && !loading && (
        <div
          data-testid="assembly-unavailable"
          className="rounded-md border border-amber-500/50 bg-amber-500/10 px-3 py-2 text-xs text-amber-700 dark:text-amber-400"
        >
          {t('parliament.unavailable')}
        </div>
      )}
      <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
        {/* ── Ideology map: party territories ── */}
        <svg
          ref={svgRef}
          viewBox={`0 0 ${SVG} ${SVG}`}
          role="img"
          aria-label={t('parliament.mapAria')}
          className="mx-auto block w-full touch-none select-none rounded-lg bg-card"
          style={{ maxWidth: 460, maxHeight: '52vh' }}
        >
          <g data-testid="party-territories" opacity={0.16}>
            {territories.map((t, i) => (
              <path key={t.name} d={t.path} fill={colorOf(i)} />
            ))}
          </g>
          <rect
            x={MARGIN}
            y={MARGIN}
            width={PLOT}
            height={PLOT}
            fill="none"
            stroke="var(--bs-border-color, #ccc)"
          />
          {/* Voters coloured by nearest party — re-attach live during drag */}
          <g>
            {voters.map((v, i) => (
              <circle
                key={i}
                cx={toSvg(v.x, 'x')}
                cy={toSvg(v.y, 'y')}
                r={1.7}
                fill={colorOf(nearestParty[i])}
                opacity={0.55}
              />
            ))}
          </g>
          {/* Congruence overlay (FB-1): ✚ electorate median · ● assembly · ◆ government */}
          {result && (
            <g data-testid="congruence-overlay">
              <g
                transform={`translate(${toSvg(result.congruence.electorate_median[0], 'x')}, ${toSvg(result.congruence.electorate_median[1], 'y')})`}
              >
                <line x1={-7} x2={7} y1={0} y2={0} stroke="#111827" strokeWidth={2} />
                <line x1={0} x2={0} y1={-7} y2={7} stroke="#111827" strokeWidth={2} />
              </g>
              <circle
                cx={toSvg(result.congruence.assembly_position[0], 'x')}
                cy={toSvg(result.congruence.assembly_position[1], 'y')}
                r={6}
                fill="none"
                stroke="#111827"
                strokeWidth={2.5}
                style={{ transition: 'cx 400ms ease, cy 400ms ease' }}
              />
              {result.congruence.governing_position && (
                <rect
                  x={toSvg(result.congruence.governing_position[0], 'x') - 5}
                  y={toSvg(result.congruence.governing_position[1], 'y') - 5}
                  width={10}
                  height={10}
                  transform={`rotate(45 ${toSvg(result.congruence.governing_position[0], 'x')} ${toSvg(result.congruence.governing_position[1], 'y')})`}
                  fill="none"
                  stroke="#111827"
                  strokeWidth={2}
                />
              )}
            </g>
          )}

          {/* Draggable parties */}
          <g>
            {parties.map((p, i) => (
              <g
                key={`${p.name}-${i}`}
                data-testid={`party-${i}`}
                style={{ cursor: 'grab' }}
                onMouseDown={(e) => {
                  e.preventDefault();
                  draggingIdx.current = i;
                }}
                onTouchStart={() => {
                  draggingIdx.current = i;
                }}
              >
                <rect
                  x={toSvg(p.x, 'x') - 8}
                  y={toSvg(p.y, 'y') - 8}
                  width={16}
                  height={16}
                  rx={3}
                  fill={colorOf(i)}
                  stroke="#fff"
                  strokeWidth={2}
                />
                <text
                  x={toSvg(p.x, 'x')}
                  y={toSvg(p.y, 'y') - 12}
                  textAnchor="middle"
                  fontSize={11}
                  fontWeight={600}
                  fill="currentColor"
                >
                  {p.name}
                </text>
              </g>
            ))}
          </g>
        </svg>

        {/* ── Hemicycle + metrics ── */}
        <div className="flex flex-col gap-2">
          <svg
            viewBox={`0 0 ${SVG} 272`}
            width="100%"
            role="img"
            aria-label={t('parliament.hemicycleAria')}
            className="rounded-lg bg-card"
          >
            <g data-testid="hemicycle">
              {seats.map((s, i) => (
                <circle
                  key={i}
                  cx={s.x}
                  cy={s.y}
                  r={Math.max(2.4, 5.5 - seats.length / 90)}
                  fill={colorOf(s.party)}
                  style={{ transition: 'fill 400ms ease' }}
                />
              ))}
            </g>
            <text
              x={SVG / 2}
              y={266}
              textAnchor="middle"
              fontSize={12}
              fill="currentColor"
              opacity={result ? 1 : 0.6}
            >
              {result
                ? `${t('parliament.seatsLine', {
                    seats: result.assembly_size,
                    majority: result.majority,
                  })}${loading ? ' · …' : ''}`
                : loading
                  ? t('parliament.computing')
                  : t('parliament.awaiting', { seats: Math.max(10, nominalSeats) })}
            </text>
          </svg>

          {/* Headline metrics */}
          {result && (
            <div
              data-testid="assembly-metrics"
              className="grid grid-cols-3 gap-2 text-center text-xs"
            >
              <div
                className="rounded-md border border-border px-1 py-1.5"
                title={t('parliament.gallagherTitle')}
              >
                <div className="font-semibold tabular-nums">
                  {result.gallagher_index?.toFixed(1) ?? '—'}
                </div>
                <div className="text-muted-foreground">{t('parliament.disproportion')}</div>
              </div>
              <div
                className="rounded-md border border-border px-1 py-1.5"
                title={t('parliament.effPartiesTitle')}
              >
                <div className="font-semibold tabular-nums">
                  {result.effective_parties_seats?.toFixed(1) ?? '—'}
                </div>
                <div className="text-muted-foreground">{t('parliament.effParties')}</div>
              </div>
              <div
                className="rounded-md border border-border px-1 py-1.5"
                title={t('parliament.wastedTitle')}
              >
                <div className="font-semibold tabular-nums">
                  {Math.round(result.wasted_vote_share * 100)} %
                </div>
                <div className="text-muted-foreground">{t('parliament.wasted')}</div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Votes% → Seats% bars (the disproportionality staircase) ── */}
      {result && (
        <div data-testid="votes-seats-bars" className="flex flex-col gap-1.5">
          {result.parties.map((p) => {
            const idx = parties.findIndex((q) => q.name === p.name);
            return (
              <div key={p.name} className="flex items-center gap-2 text-xs">
                <button
                  type="button"
                  data-testid={`coalition-toggle-${p.name}`}
                  onClick={() => toggleCoalition(p.name)}
                  className={cn(
                    'w-24 truncate rounded border px-1.5 py-0.5 text-left transition-colors',
                    coalition.has(p.name)
                      ? 'border-transparent text-white'
                      : 'border-border hover:bg-accent'
                  )}
                  style={coalition.has(p.name) ? { background: colorOf(idx) } : undefined}
                  title={t('parliament.coalitionToggleTitle')}
                >
                  {p.name}
                </button>
                <div className="relative h-4 flex-1 overflow-hidden rounded bg-muted/50">
                  {/* votes (hatched underlay) */}
                  <div
                    className="absolute inset-y-0 left-0 opacity-35"
                    style={{
                      width: `${p.vote_share * 100}%`,
                      background: colorOf(idx),
                      transition: 'width 400ms ease',
                    }}
                  />
                  {/* seats (solid) */}
                  <div
                    className="absolute left-0 top-1 h-2"
                    style={{
                      width: `${p.seat_share * 100}%`,
                      background: colorOf(idx),
                      transition: 'width 400ms ease',
                    }}
                  />
                </div>
                <span className="w-28 text-right tabular-nums text-muted-foreground">
                  {(p.vote_share * 100).toFixed(1)} % → {(p.seat_share * 100).toFixed(1)} %
                  {p.excluded_by_threshold ? ' ✕' : ''}
                </span>
              </div>
            );
          })}
          <p className="text-[0.7rem] text-muted-foreground">{t('parliament.votesSeatsNote')}</p>
        </div>
      )}

      {/* ── Representation → governance (FB-1): congruence + descriptive mirror ── */}
      {result && (
        <div className="grid grid-cols-1 gap-2 xl:grid-cols-2">
          <div
            data-testid="congruence-readout"
            className="rounded-md border border-border px-3 py-2 text-xs"
            title={t('parliament.congruenceTitle')}
          >
            <p className="font-semibold uppercase tracking-wide text-muted-foreground">
              {t('parliament.congruenceHead')}
            </p>
            <p className="mt-1 tabular-nums">
              {t('parliament.gapLine')} <strong>{result.congruence.assembly_gap.toFixed(2)}</strong>
              {result.congruence.governing_gap !== null && (
                <>
                  {' · '}
                  {t('parliament.governingCoalition')}{' '}
                  <strong>{result.congruence.governing_gap.toFixed(2)}</strong>
                </>
              )}
            </p>
          </div>

          <div data-testid="mirror-bars" className="rounded-md border border-border px-3 py-2">
            <p
              className="text-xs font-semibold uppercase tracking-wide text-muted-foreground"
              title={t('parliament.mirrorTitle')}
            >
              {t('parliament.mirrorHead')}
            </p>
            <div className="mt-1 flex flex-col gap-1">
              {result.mirror.map((m) => (
                <div key={m.region} className="flex items-center gap-2 text-[0.7rem]">
                  <span className="w-28 shrink-0 truncate text-muted-foreground">
                    {t(`parliament.mirror.${m.region}`, { defaultValue: m.region })}
                  </span>
                  <div className="relative h-3.5 flex-1 overflow-hidden rounded bg-muted/50">
                    <div
                      className="absolute inset-y-0 left-0 bg-slate-400/50"
                      style={{
                        width: `${m.electorate_share * 100}%`,
                        transition: 'width 400ms ease',
                      }}
                    />
                    <div
                      className="absolute left-0 top-1 h-1.5 bg-primary"
                      style={{
                        width: `${m.assembly_share * 100}%`,
                        transition: 'width 400ms ease',
                      }}
                    />
                  </div>
                  <span className="w-20 text-right tabular-nums text-muted-foreground">
                    {Math.round(m.electorate_share * 100)} % → {Math.round(m.assembly_share * 100)}{' '}
                    %
                  </span>
                </div>
              ))}
            </div>
            <p className="mt-1 text-[0.65rem] text-muted-foreground">
              {t('parliament.mirrorNote')}
            </p>
          </div>
        </div>
      )}

      {/* ── Coalition builder ── */}
      {result && (
        <div
          data-testid="coalition-status"
          className={cn(
            'rounded-md border px-3 py-2 text-sm',
            coalition.size === 0
              ? 'border-border text-muted-foreground'
              : coalitionSeats >= result.majority
                ? 'border-green-600/50'
                : 'border-border'
          )}
        >
          {coalition.size === 0 ? (
            <>{t('parliament.coalitionEmpty', { majority: result.majority })}</>
          ) : (
            <>
              {t('parliament.coalitionLabel')} <strong>{coalitionSeats}</strong> / {result.majority}{' '}
              {t('parliament.seatsWord')}
              {coalitionSeats >= result.majority
                ? t('parliament.coalitionMajority')
                : t('parliament.coalitionNoMajority')}
              {t('parliament.coalitionSpan', { span: coalitionSpan.toFixed(2) })}
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default ParliamentCanvas;
