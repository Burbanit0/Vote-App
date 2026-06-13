import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  fieldWinnerName,
  winRegionGrid,
  RULE_LABELS,
  type Dims,
  type NamedPt,
  type Pt,
  type Rule,
  type WinRegion,
} from '../../lib/playgroundVoting';
import LeaderScene3D from './LeaderScene3D';

// LeaderCanvas (Lab reshape P2 · dims FA-2bis) — the live single-office viz over
// a 1/2/3-D ideological space. Candidates are draggable; the plane is shaded by
// the win/entry-region overlay. 1-D collapses to a number line (the median-voter
// theorem made literal); 3-D keeps the x–y map for direct manipulation, edits the
// 3rd axis with per-candidate z sliders, and reads the overlay as a z=0 slice.
// All winner math is genuinely N-D (distances include z).

const SVG = 480;
const MARGIN = 28;
const PLOT = SVG - 2 * MARGIN;
const CENTER = SVG / 2;
const GRID_N = 16;
const VOTER_CAP = 160;

const PALETTE = [
  '#2563eb', '#dc2626', '#16a34a', '#9333ea',
  '#ea580c', '#0891b2', '#ca8a04', '#db2777',
];
const ENTRY_COLOR = '#fbbf24';

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

const median = (xs: number[]): number => {
  if (!xs.length) return 0;
  const s = [...xs].sort((a, b) => a - b);
  const mid = Math.floor(s.length / 2);
  return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
};

export interface LeaderCanvasProps {
  candidates: NamedPt[];
  voters: Pt[];
  rule: Rule;
  dims: Dims;
  onRuleChange: (rule: Rule) => void;
  onMoveCandidate: (index: number, x: number, y: number, z?: number) => void;
}

const LeaderCanvas: React.FC<LeaderCanvasProps> = ({
  candidates,
  voters,
  rule,
  dims,
  onRuleChange,
  onMoveCandidate,
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const draggingIdx = useRef<number | null>(null);
  const [region, setRegion] = useState<WinRegion | null>(null);
  // In 3-D, default to the orbital scene (what the dimension is *for*); the
  // x–y plane stays available for editing + the win-region overlay.
  const [scene3d, setScene3d] = useState(true);
  const show3d = dims === 3 && scene3d;

  // y maps to the plane in 2/3-D, to the centre line in 1-D.
  const cyOf = (p: Pt): number => (dims === 1 ? CENTER : toSvg(p.y, 'y'));

  const gridVoters = useMemo(
    () =>
      voters.length > VOTER_CAP
        ? voters.filter((_, i) => i % Math.ceil(voters.length / VOTER_CAP) === 0)
        : voters,
    [voters]
  );

  useEffect(() => {
    let alive = true;
    const t = setTimeout(() => {
      if (!alive) return;
      setRegion(winRegionGrid(gridVoters, candidates, rule, GRID_N, dims));
    }, 120);
    return () => {
      alive = false;
      clearTimeout(t);
    };
  }, [gridVoters, candidates, rule, dims]);

  useEffect(() => {
    const move = (clientX: number, clientY: number) => {
      if (draggingIdx.current === null || !svgRef.current) return;
      const { x, y } = svgToDomain(clientX, clientY, svgRef.current.getBoundingClientRect());
      onMoveCandidate(draggingIdx.current, x, dims === 1 ? 0 : y);
    };
    const onMM = (e: MouseEvent) => move(e.clientX, e.clientY);
    const onUp = () => { draggingIdx.current = null; };
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
  }, [onMoveCandidate, dims]);

  const winner = fieldWinnerName(voters, candidates, rule);
  const mx = median(voters.map((v) => v.x));
  const my = median(voters.map((v) => v.y));
  const cellW = PLOT / GRID_N;

  const colorFor = (idx: number): string =>
    idx === candidates.length ? ENTRY_COLOR : PALETTE[idx % PALETTE.length];

  return (
    <div data-testid="leader-canvas" data-dims={dims} className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <label className="flex items-center gap-2 text-sm">
          <span className="text-muted-foreground">Règle</span>
          <select
            data-testid="rule-select"
            className="rounded-md border border-input bg-background px-2 py-1 text-sm"
            value={rule}
            onChange={(e) => onRuleChange(e.target.value as Rule)}
          >
            {(Object.keys(RULE_LABELS) as Rule[]).map((r) => (
              <option key={r} value={r}>{RULE_LABELS[r]}</option>
            ))}
          </select>
        </label>
        <span data-testid="field-winner" className="text-sm">
          Vainqueur : <strong>{winner ?? '—'}</strong>
        </span>
      </div>

      {/* 3-D view toggle: orbital scene vs the editable x–y plane. */}
      {dims === 3 && (
        <div className="flex gap-1 text-xs">
          <button
            type="button"
            data-testid="view-3d"
            className={`rounded border px-2 py-0.5 ${scene3d ? 'border-primary text-primary' : 'border-border'}`}
            onClick={() => setScene3d(true)}
          >
            🧊 Vue 3D
          </button>
          <button
            type="button"
            data-testid="view-plane"
            className={`rounded border px-2 py-0.5 ${!scene3d ? 'border-primary text-primary' : 'border-border'}`}
            onClick={() => setScene3d(false)}
          >
            ▦ Plan x–y (édition)
          </button>
        </div>
      )}

      {show3d && (
        <LeaderScene3D voters={voters} candidates={candidates} palette={PALETTE} />
      )}

      <svg
        ref={svgRef}
        viewBox={`0 0 ${SVG} ${SVG}`}
        width="100%"
        role="img"
        aria-label="Carte idéologique — élire un dirigeant"
        className="touch-none select-none rounded-lg bg-card"
        style={{ maxHeight: '70vh', display: show3d ? 'none' : undefined }}
      >
        {/* Win/entry-region overlay (full-height columns in 1-D) */}
        <g data-testid="winregion" opacity={0.28}>
          {region &&
            region.cells.map((widx, k) => {
              const cellH = PLOT / region.rows;
              const r = Math.floor(k / region.n);
              const c = k % region.n;
              return (
                <rect
                  key={k}
                  x={MARGIN + c * cellW}
                  y={MARGIN + r * cellH}
                  width={cellW + 0.5}
                  height={cellH + 0.5}
                  fill={colorFor(widx)}
                />
              );
            })}
        </g>

        {/* Plot border + axes */}
        <rect x={MARGIN} y={MARGIN} width={PLOT} height={PLOT} fill="none" stroke="var(--bs-border-color, #ccc)" />
        <line x1={MARGIN} y1={dims === 1 ? CENTER : toSvg(0, 'y')} x2={MARGIN + PLOT} y2={dims === 1 ? CENTER : toSvg(0, 'y')} stroke="var(--bs-border-color, #ddd)" strokeDasharray="3 3" />
        {dims !== 1 && (
          <line x1={toSvg(0, 'x')} y1={MARGIN} x2={toSvg(0, 'x')} y2={MARGIN + PLOT} stroke="var(--bs-border-color, #ddd)" strokeDasharray="3 3" />
        )}

        {/* Voters */}
        <g>
          {voters.map((v, i) => (
            <circle key={i} cx={toSvg(v.x, 'x')} cy={cyOf(v)} r={1.6} fill="#64748b" opacity={0.5} />
          ))}
        </g>

        {/* Median-voter marker */}
        <g data-testid="median-marker">
          <circle cx={toSvg(mx, 'x')} cy={dims === 1 ? CENTER : toSvg(my, 'y')} r={5} fill="none" stroke="#111827" strokeWidth={1.5} />
          <line x1={toSvg(mx, 'x') - 8} y1={dims === 1 ? CENTER : toSvg(my, 'y')} x2={toSvg(mx, 'x') + 8} y2={dims === 1 ? CENTER : toSvg(my, 'y')} stroke="#111827" strokeWidth={1} />
          {dims !== 1 && (
            <line x1={toSvg(mx, 'x')} y1={toSvg(my, 'y') - 8} x2={toSvg(mx, 'x')} y2={toSvg(my, 'y') + 8} stroke="#111827" strokeWidth={1} />
          )}
        </g>

        {/* Draggable candidates (z shown as an outer ring in 3-D) */}
        <g>
          {candidates.map((cand, i) => {
            const cx = toSvg(cand.x, 'x');
            const cy = cyOf(cand);
            const zr = dims === 3 ? 9 + Math.abs(cand.z ?? 0) * 12 : 0;
            return (
              <g
                key={`${cand.name}-${i}`}
                data-testid={`candidate-${i}`}
                style={{ cursor: 'grab' }}
                onMouseDown={(e) => { e.preventDefault(); draggingIdx.current = i; }}
                onTouchStart={() => { draggingIdx.current = i; }}
              >
                {dims === 3 && (cand.z ?? 0) !== 0 && (
                  <circle cx={cx} cy={cy} r={zr} fill="none" stroke={PALETTE[i % PALETTE.length]} strokeWidth={1} strokeDasharray="2 2" opacity={0.7} />
                )}
                <circle cx={cx} cy={cy} r={9} fill={PALETTE[i % PALETTE.length]} stroke="#fff" strokeWidth={2} />
                <text x={cx} y={cy - 13} textAnchor="middle" fontSize={11} fontWeight={600} fill="currentColor">
                  {cand.name}
                  {dims === 3 && (cand.z ?? 0) !== 0 ? ` (z ${(cand.z ?? 0).toFixed(1)})` : ''}
                </text>
              </g>
            );
          })}
        </g>
      </svg>

      {/* 3-D depth controls — the z axis can't be dragged on a 2-D plane. */}
      {dims === 3 && (
        <div data-testid="z-controls" className="flex flex-col gap-1 rounded-md border border-border p-2">
          <span className="text-[0.7rem] font-medium text-muted-foreground">
            Axe z (profondeur) — réglé par curseur
          </span>
          {candidates.map((cand, i) => (
            <label key={i} className="flex items-center gap-2 text-xs">
              <span className="w-20 shrink-0 truncate" style={{ color: PALETTE[i % PALETTE.length] }}>
                {cand.name}
              </span>
              <input
                data-testid={`z-slider-${i}`}
                type="range"
                className="flex-1"
                min={-1}
                max={1}
                step={0.05}
                value={cand.z ?? 0}
                onChange={(e) => onMoveCandidate(i, cand.x, cand.y, Number(e.target.value))}
              />
              <span className="w-8 text-right tabular-nums text-muted-foreground">
                {(cand.z ?? 0).toFixed(1)}
              </span>
            </label>
          ))}
        </div>
      )}

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
        {candidates.map((c, i) => (
          <span key={i} className="flex items-center gap-1">
            <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: PALETTE[i % PALETTE.length] }} />
            {c.name}
          </span>
        ))}
        <span className="flex items-center gap-1">
          <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: ENTRY_COLOR }} />
          Zone d’un nouvel entrant
        </span>
      </div>
      <p className="text-xs text-muted-foreground/70">
        {dims === 1 &&
          'Espace à 1 dimension : tout se joue sur un axe — le terrain du théorème de l’électeur médian.'}
        {dims === 2 &&
          'Glissez les candidats. Les zones colorées montrent qui gagnerait si un candidat était placé là — les frontières révèlent les régions vulnérables au vote stratégique.'}
        {dims === 3 && show3d &&
          'Vue 3D orbitale : glissez pour pivoter, les électeurs sont colorés par candidat le plus proche (en 3-D). Basculez en « Plan x–y » pour éditer et voir l’overlay.'}
        {dims === 3 && !show3d &&
          'Plan x–y (réglez z au curseur) ; le calcul du vainqueur est bien en 3-D, mais l’overlay n’est qu’une tranche z=0.'}
      </p>
    </div>
  );
};

export default LeaderCanvas;
