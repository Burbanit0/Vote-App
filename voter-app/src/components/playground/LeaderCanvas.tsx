import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  fieldWinnerName,
  winRegionGrid,
  RULE_LABELS,
  type NamedPt,
  type Pt,
  type Rule,
  type WinRegion,
} from '../../lib/playgroundVoting';

// LeaderCanvas (Lab reshape P2) — the live single-office viz. Candidates are
// draggable; the plane is shaded by the win/entry-region overlay ("a hypothetical
// candidate placed HERE would win against the field under the selected rule"),
// which reflows during drag with no Run button. The backend profile engine fills
// the precise scorecard separately (on drag-release, via the page).

const SVG = 480;
const MARGIN = 28;
const PLOT = SVG - 2 * MARGIN;
const GRID_N = 16;
const VOTER_CAP = 160; // subsample for the live grid so drag stays < ~100 ms

const PALETTE = [
  '#2563eb', '#dc2626', '#16a34a', '#9333ea',
  '#ea580c', '#0891b2', '#ca8a04', '#db2777',
];
const ENTRY_COLOR = '#fbbf24'; // a hypothetical new entrant would win here

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
  onRuleChange: (rule: Rule) => void;
  onMoveCandidate: (index: number, x: number, y: number) => void;
}

const LeaderCanvas: React.FC<LeaderCanvasProps> = ({
  candidates,
  voters,
  rule,
  onRuleChange,
  onMoveCandidate,
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const draggingIdx = useRef<number | null>(null);
  const [region, setRegion] = useState<WinRegion | null>(null);

  // Cap the voter set used for the (expensive) grid so dragging stays smooth.
  const gridVoters = useMemo(
    () => (voters.length > VOTER_CAP ? voters.filter((_, i) => i % Math.ceil(voters.length / VOTER_CAP) === 0) : voters),
    [voters]
  );

  // Live win/entry-region overlay — debounced recompute on any change.
  useEffect(() => {
    let alive = true;
    const t = setTimeout(() => {
      if (!alive) return;
      setRegion(winRegionGrid(gridVoters, candidates, rule, GRID_N));
    }, 120);
    return () => {
      alive = false;
      clearTimeout(t);
    };
  }, [gridVoters, candidates, rule]);

  // Unified mouse + touch drag. Window-level mousemove captures fast pointer
  // movement; touch stays on the SVG so idle scrolling isn't blocked.
  useEffect(() => {
    const move = (clientX: number, clientY: number) => {
      if (draggingIdx.current === null || !svgRef.current) return;
      const { x, y } = svgToDomain(clientX, clientY, svgRef.current.getBoundingClientRect());
      onMoveCandidate(draggingIdx.current, x, y);
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
  }, [onMoveCandidate]);

  const winner = fieldWinnerName(voters, candidates, rule);
  const mx = median(voters.map((v) => v.x));
  const my = median(voters.map((v) => v.y));
  const cellW = PLOT / GRID_N;

  const colorFor = (idx: number): string =>
    idx === candidates.length ? ENTRY_COLOR : PALETTE[idx % PALETTE.length];

  return (
    <div data-testid="leader-canvas" className="flex flex-col gap-2">
      {/* Rule selector + field winner */}
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
              <option key={r} value={r}>
                {RULE_LABELS[r]}
              </option>
            ))}
          </select>
        </label>
        <span data-testid="field-winner" className="text-sm">
          Vainqueur : <strong>{winner ?? '—'}</strong>
        </span>
      </div>

      <svg
        ref={svgRef}
        viewBox={`0 0 ${SVG} ${SVG}`}
        width="100%"
        role="img"
        aria-label="Carte idéologique — élire un dirigeant"
        className="touch-none select-none rounded-lg bg-card"
        style={{ maxHeight: '70vh' }}
      >
        {/* Win/entry-region overlay */}
        <g data-testid="winregion" opacity={0.28}>
          {region &&
            region.cells.map((widx, k) => {
              const r = Math.floor(k / region.n);
              const c = k % region.n;
              return (
                <rect
                  key={k}
                  x={MARGIN + c * cellW}
                  y={MARGIN + r * cellW}
                  width={cellW + 0.5}
                  height={cellW + 0.5}
                  fill={colorFor(widx)}
                />
              );
            })}
        </g>

        {/* Plot border + axes */}
        <rect x={MARGIN} y={MARGIN} width={PLOT} height={PLOT} fill="none" stroke="var(--bs-border-color, #ccc)" />
        <line x1={MARGIN} y1={toSvg(0, 'y')} x2={MARGIN + PLOT} y2={toSvg(0, 'y')} stroke="var(--bs-border-color, #ddd)" strokeDasharray="3 3" />
        <line x1={toSvg(0, 'x')} y1={MARGIN} x2={toSvg(0, 'x')} y2={MARGIN + PLOT} stroke="var(--bs-border-color, #ddd)" strokeDasharray="3 3" />

        {/* Voters */}
        <g>
          {voters.map((v, i) => (
            <circle key={i} cx={toSvg(v.x, 'x')} cy={toSvg(v.y, 'y')} r={1.6} fill="#64748b" opacity={0.5} />
          ))}
        </g>

        {/* Median-voter marker */}
        <g data-testid="median-marker">
          <circle cx={toSvg(mx, 'x')} cy={toSvg(my, 'y')} r={5} fill="none" stroke="#111827" strokeWidth={1.5} />
          <line x1={toSvg(mx, 'x') - 8} y1={toSvg(my, 'y')} x2={toSvg(mx, 'x') + 8} y2={toSvg(my, 'y')} stroke="#111827" strokeWidth={1} />
          <line x1={toSvg(mx, 'x')} y1={toSvg(my, 'y') - 8} x2={toSvg(mx, 'x')} y2={toSvg(my, 'y') + 8} stroke="#111827" strokeWidth={1} />
        </g>

        {/* Draggable candidates */}
        <g>
          {candidates.map((cand, i) => (
            <g
              key={`${cand.name}-${i}`}
              data-testid={`candidate-${i}`}
              style={{ cursor: 'grab' }}
              onMouseDown={(e) => {
                e.preventDefault();
                draggingIdx.current = i;
              }}
              onTouchStart={() => {
                draggingIdx.current = i;
              }}
            >
              <circle
                cx={toSvg(cand.x, 'x')}
                cy={toSvg(cand.y, 'y')}
                r={9}
                fill={PALETTE[i % PALETTE.length]}
                stroke="#fff"
                strokeWidth={2}
              />
              <text x={toSvg(cand.x, 'x')} y={toSvg(cand.y, 'y') - 13} textAnchor="middle" fontSize={11} fontWeight={600} fill="currentColor">
                {cand.name}
              </text>
            </g>
          ))}
        </g>
      </svg>

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
        Glissez les candidats. Les zones colorées indiquent qui gagnerait si un candidat
        était placé là — les frontières révèlent les régions vulnérables au vote stratégique.
      </p>
    </div>
  );
};

export default LeaderCanvas;
