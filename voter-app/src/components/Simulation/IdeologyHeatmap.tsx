/**
 * IdeologyHeatmap — 30×30 density + winner heatmap for the ideology space.
 *
 * Algorithm:
 *   1. Bucket each voter into a grid cell (floor-based, O(N_voters))
 *   2. Colour = nearest candidate (Voronoi-like), saturated by local density
 *   3. Contour lines between zones with different winners
 *   4. Candidate ★ markers rendered on top (draggable via parent)
 *   5. CSS transition on rect fill for smooth recoloring after drag
 */
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Badge } from '@/components/ui/badge';
import { useSimulationWorker } from '../../hooks/useSimulationWorker';
import {
  GRID_N,
  computeGrid,
  type HeatmapVoter,
  type HeatmapCandidate,
  type GridCell,
  type HeatmapMetrics,
} from '../../lib/simulationKernels';

// ── Constants ─────────────────────────────────────────────────────────────────

const SVG_W = 480;
const SVG_H = 480;
const MARGIN = 40;
const PLOT_W = SVG_W - 2 * MARGIN;
const PLOT_H = SVG_H - 2 * MARGIN;
const CELL_W = PLOT_W / GRID_N;
const CELL_H = PLOT_H / GRID_N;

const CANDIDATE_COLORS = ['#005CAB', '#C8590A', '#007A33', '#6c757d', '#9b59b6', '#e67e22'];

// ── Types + pure grid computation live in lib/simulationKernels (the Web Worker
//    imports them, and a worker cannot pull in React/i18n). Re-exported here so
//    existing importers of this module are unaffected. ─────────────────────────

export {
  GRID_N,
  computeGrid,
  type HeatmapVoter,
  type HeatmapCandidate,
  type GridCell,
  type HeatmapMetrics,
};

// ── SVG coordinate helpers ────────────────────────────────────────────────────

function cellRect(i: number, j: number) {
  // j=0 → domain y=-1 → bottom of SVG → high SVG y
  const x = MARGIN + i * CELL_W;
  const y = MARGIN + (GRID_N - 1 - j) * CELL_H;
  return { x, y, w: CELL_W, h: CELL_H };
}

function domainToSvg(v: number, axis: 'x' | 'y'): number {
  if (axis === 'x') return MARGIN + ((v + 1) / 2) * PLOT_W;
  return MARGIN + ((1 - v) / 2) * PLOT_H;
}

// ── Component ─────────────────────────────────────────────────────────────────

export interface IdeologyHeatmapProps {
  voters: HeatmapVoter[];
  candidates: HeatmapCandidate[];
  colors?: string[];
  /** Called when a candidate mousedown event fires */
  onCandidateMouseDown?: (e: React.MouseEvent, idx: number) => void;
  draggingIdx?: number | null;
  gridN?: number;
}

const IdeologyHeatmap = React.forwardRef<SVGSVGElement, IdeologyHeatmapProps>(
  ({ voters, candidates, colors, onCandidateMouseDown, draggingIdx, gridN = GRID_N }, ref) => {
    const { t } = useTranslation();
    const { dispatch, isComputing } = useSimulationWorker();

    const candColors =
      colors ?? candidates.map((_, i) => CANDIDATE_COLORS[i % CANDIDATE_COLORS.length]);

    // ── Async grid computation via Web Worker ─────────────────────────────
    const [cells, setCells] = useState<GridCell[]>([]);
    const [metrics, setMetrics] = useState<HeatmapMetrics>({
      maxContestedCell: null,
      fortressCell: null,
      fortressCandidate: null,
      maxDensity: 1,
    });
    const abortRef = useRef<string | null>(null); // track last dispatch id to ignore stale results

    useEffect(() => {
      const dispatchId = `${Date.now()}`;
      abortRef.current = dispatchId;

      dispatch('COMPUTE_HEATMAP', { voters, candidates, gridN })
        .then(({ cells: c, metrics: m }) => {
          if (abortRef.current !== dispatchId) return; // stale — discard
          setCells(c);
          setMetrics(m);
        })
        .catch(() => {
          // Fallback: compute synchronously if worker unavailable
          const result = computeGrid(voters, candidates, gridN);
          if (abortRef.current === dispatchId) {
            setCells(result.cells);
            setMetrics(result.metrics);
          }
        });
    }, [voters, candidates, gridN, dispatch]);

    // Contour lines: adjacent cells with different winners
    const contourLines = useMemo(() => {
      const lines: { x1: number; y1: number; x2: number; y2: number }[] = [];
      const N = gridN;
      const idx = (i: number, j: number) => j * N + i;

      for (let j = 0; j < N; j++) {
        for (let i = 0; i < N; i++) {
          const w = cells[idx(i, j)]?.winnerIdx;
          if (w < 0) continue;

          // Right neighbour
          if (i + 1 < N) {
            const wr = cells[idx(i + 1, j)]?.winnerIdx;
            if (wr >= 0 && wr !== w) {
              const { x, y } = cellRect(i, j);
              lines.push({ x1: x + CELL_W, y1: y, x2: x + CELL_W, y2: y + CELL_H });
            }
          }
          // Top neighbour (j+1 = higher domain y = lower SVG y)
          if (j + 1 < N) {
            const wt = cells[idx(i, j + 1)]?.winnerIdx;
            if (wt >= 0 && wt !== w) {
              const { x, y } = cellRect(i, j + 1);
              lines.push({ x1: x, y1: y + CELL_H, x2: x + CELL_W, y2: y + CELL_H });
            }
          }
        }
      }
      return lines;
    }, [cells, gridN]);

    return (
      <div>
        <svg
          ref={ref}
          data-testid="heatmap-svg"
          viewBox={`0 0 ${SVG_W} ${SVG_H}`}
          width="100%"
          style={{
            maxHeight: 520,
            display: 'block',
            userSelect: 'none',
            cursor: draggingIdx != null ? 'grabbing' : 'crosshair',
          }}
        >
          {/* ── Skeleton while computing ── */}
          {isComputing && cells.length === 0 && (
            <g data-testid="heatmap-skeleton" opacity={0.4}>
              {Array.from({ length: GRID_N * GRID_N }, (_, k) => {
                const i = k % GRID_N;
                const j = Math.floor(k / GRID_N);
                const { x, y, w, h } = cellRect(i, j);
                return (
                  <rect key={k} x={x} y={y} width={w} height={h} fill="#dee2e6">
                    <animate
                      attributeName="fill-opacity"
                      values="0.3;0.7;0.3"
                      dur="1.6s"
                      begin={`${(i + j) * 0.02}s`}
                      repeatCount="indefinite"
                    />
                  </rect>
                );
              })}
            </g>
          )}

          {/* ── Heatmap cells ── */}
          <g
            data-testid="heatmap-cells"
            style={{ opacity: isComputing ? 0.6 : 1, transition: 'opacity 0.3s' }}
          >
            {cells.map((cell) => {
              const { x, y, w, h } = cellRect(cell.i, cell.j);
              const opacity =
                cell.density === 0 ? 0 : 0.15 + (cell.density / metrics.maxDensity) * 0.75;
              const fill = cell.winnerIdx >= 0 ? candColors[cell.winnerIdx] : '#dee2e6';
              return (
                <rect
                  key={`${cell.i}-${cell.j}`}
                  data-testid="heatmap-cell"
                  x={x}
                  y={y}
                  width={w}
                  height={h}
                  fill={fill}
                  fillOpacity={opacity}
                  style={{ transition: 'fill 0.5s ease, fill-opacity 0.3s' }}
                />
              );
            })}
          </g>

          {/* ── Contour lines (zone boundaries) ── */}
          <g data-testid="contour-lines" pointerEvents="none">
            {contourLines.map((l, i) => (
              <line
                key={i}
                x1={l.x1}
                y1={l.y1}
                x2={l.x2}
                y2={l.y2}
                stroke="#fff"
                strokeWidth={0.7}
                strokeOpacity={0.6}
              />
            ))}
          </g>

          {/* ── Grid axes ── */}
          <line
            x1={SVG_W / 2}
            y1={MARGIN}
            x2={SVG_W / 2}
            y2={SVG_H - MARGIN}
            stroke="#adb5bd"
            strokeWidth={1}
          />
          <line
            x1={MARGIN}
            y1={SVG_H / 2}
            x2={SVG_W - MARGIN}
            y2={SVG_H / 2}
            stroke="#adb5bd"
            strokeWidth={1}
          />

          {/* ── Border ── */}
          <rect
            x={MARGIN}
            y={MARGIN}
            width={PLOT_W}
            height={PLOT_H}
            fill="none"
            stroke="#dee2e6"
            strokeWidth={1}
          />

          {/* ── Axis labels ── */}
          <text x={MARGIN} y={SVG_H - 6} fontSize={10} fill="#6c757d">
            {t('ideologyMap.axisLeft')}
          </text>
          <text x={SVG_W - MARGIN} y={SVG_H - 6} textAnchor="end" fontSize={10} fill="#6c757d">
            {t('ideologyMap.axisRight')}
          </text>

          {/* ── Contested zone highlight ── */}
          {metrics.maxContestedCell &&
            metrics.maxContestedCell.density > 0 &&
            (() => {
              const { x, y, w, h } = cellRect(
                metrics.maxContestedCell.i,
                metrics.maxContestedCell.j
              );
              return (
                <rect
                  x={x - 2}
                  y={y - 2}
                  width={w + 4}
                  height={h + 4}
                  fill="none"
                  stroke="#dc3545"
                  strokeWidth={1.5}
                  strokeDasharray="3 2"
                  data-testid="contested-highlight"
                />
              );
            })()}

          {/* ── Candidate markers (★) ── */}
          {candidates.map((cp, idx) => {
            const cx = domainToSvg(cp.x, 'x');
            const cy = domainToSvg(cp.y, 'y');
            const color = candColors[idx];
            return (
              <g
                key={cp.name}
                transform={`translate(${cx},${cy})`}
                style={{ cursor: draggingIdx === idx ? 'grabbing' : 'grab' }}
                onMouseDown={onCandidateMouseDown ? (e) => onCandidateMouseDown(e, idx) : undefined}
                data-testid={`candidate-marker-${cp.name}`}
              >
                <circle r={14} fill={color} fillOpacity={0.18} />
                <text
                  textAnchor="middle"
                  dominantBaseline="central"
                  fontSize={22}
                  fill={color}
                  stroke="#fff"
                  strokeWidth={0.8}
                  style={{ pointerEvents: 'none', userSelect: 'none' }}
                >
                  ★
                </text>
                <text
                  y={-20}
                  textAnchor="middle"
                  fontSize={11}
                  fill={color}
                  fontWeight={600}
                  stroke="#fff"
                  strokeWidth={3}
                  paintOrder="stroke"
                  style={{ pointerEvents: 'none' }}
                >
                  {cp.name}
                </text>
              </g>
            );
          })}
        </svg>

        {/* ── Metrics ── */}
        <div className="flex flex-wrap gap-3 mt-2" style={{ fontSize: '0.78rem' }}>
          {metrics.maxContestedCell && metrics.maxContestedCell.density > 0 && (
            <Badge variant="danger" data-testid="contested-badge">
              {t('heatmap.mostContested')}: ({metrics.maxContestedCell.cx.toFixed(2)},{' '}
              {metrics.maxContestedCell.cy.toFixed(2)})
            </Badge>
          )}
          {metrics.fortressCandidate &&
            metrics.fortressCell &&
            metrics.fortressCell.density > 0 && (
              <Badge
                style={{ background: candColors[metrics.fortressCell.winnerIdx] }}
                data-testid="fortress-badge"
              >
                {t('heatmap.fortress')}: {metrics.fortressCandidate}
              </Badge>
            )}
        </div>

        {/* Legend */}
        <div className="flex flex-wrap gap-3 mt-1" style={{ fontSize: '0.74rem' }}>
          {candidates.map((c, i) => (
            <span key={c.name} className="flex items-center gap-1">
              <span
                style={{
                  display: 'inline-block',
                  width: 12,
                  height: 12,
                  background: candColors[i],
                  borderRadius: 2,
                }}
              />
              {c.name}
            </span>
          ))}
          <span className="text-muted-foreground">{t('heatmap.opacityHint')}</span>
        </div>
      </div>
    );
  }
);
IdeologyHeatmap.displayName = 'IdeologyHeatmap';

export default IdeologyHeatmap;
