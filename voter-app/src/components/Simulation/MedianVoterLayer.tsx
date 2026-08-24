/**
 * MedianVoterLayer — SVG overlay that visualises the median voter theorem
 * (Duncan Black, 1948): the candidate nearest the median voter should win
 * any pairwise comparison.
 *
 * Rendered as a <g> element meant to be embedded inside the existing
 * IdeologyMapChart <svg>, sharing its coordinate system.
 */
import React, { useMemo } from 'react';
import { useTranslation } from 'react-i18next';

// ── Mirror of IdeologyMapChart SVG constants (shared coordinate system) ───────

const SVG_W = 480;
const SVG_H = 480;
const MARGIN = 40;
const PLOT_W = SVG_W - 2 * MARGIN;
const PLOT_H = SVG_H - 2 * MARGIN;

function domainToSvgX(v: number): number {
  return MARGIN + ((v + 1) / 2) * PLOT_W;
}
function domainToSvgY(v: number): number {
  return MARGIN + ((1 - v) / 2) * PLOT_H;
}

// ── Types ─────────────────────────────────────────────────────────────────────

export interface MedianVoterPoint {
  x: number;
  y: number;
}
export interface MedianCandidate {
  name: string;
  x: number;
  y: number;
}

export interface MedianVoterLayerProps {
  voters: MedianVoterPoint[];
  candidates: MedianCandidate[];
  winnerA: string | null;
  winnerB: string | null;
  methodA: string;
  methodB: string;
}

// ── Pure helpers (exported for unit tests) ────────────────────────────────────

export function computeMedian(values: number[]): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0 ? (sorted[mid - 1] + sorted[mid]) / 2 : sorted[mid];
}

export function nearestCandidate(
  mx: number,
  my: number,
  candidates: MedianCandidate[]
): MedianCandidate | null {
  if (candidates.length === 0) return null;
  return candidates.reduce((best, c) => {
    const dBest = (best.x - mx) ** 2 + (best.y - my) ** 2;
    const dC = (c.x - mx) ** 2 + (c.y - my) ** 2;
    return dC < dBest ? c : best;
  });
}

// ── Component ─────────────────────────────────────────────────────────────────

const MEDIAN_COLOR = '#e67e22'; // orange
const HIT_COLOR = '#007A33'; // green — winner matches prediction
const MISS_COLOR = '#B71C1C'; // red   — winner misses median

const MedianVoterLayer: React.FC<MedianVoterLayerProps> = ({
  voters,
  candidates,
  winnerA,
  winnerB,
  methodA,
}) => {
  const { t } = useTranslation();

  const { mx, my, predicted } = useMemo(() => {
    if (voters.length === 0 || candidates.length === 0) {
      return { mx: 0, my: 0, predicted: null };
    }
    const mxVal = computeMedian(voters.map((v) => v.x));
    const myVal = computeMedian(voters.map((v) => v.y));
    return {
      mx: mxVal,
      my: myVal,
      predicted: nearestCandidate(mxVal, myVal, candidates),
    };
  }, [voters, candidates]);

  if (!predicted) return null;

  const svgMx = domainToSvgX(mx);
  const svgMy = domainToSvgY(my);
  const svgPx = domainToSvgX(predicted.x);
  const svgPy = domainToSvgY(predicted.y);

  const matchA = winnerA === predicted.name;
  const matchB = winnerB === predicted.name;
  const colorA = matchA ? HIT_COLOR : MISS_COLOR;
  const colorB = matchB ? HIT_COLOR : MISS_COLOR;

  const crossSize = 9;

  return (
    <g data-testid="median-voter-layer" pointerEvents="none">
      {/* ── Prediction line to predicted candidate ── */}
      <line
        x1={svgMx}
        y1={svgMy}
        x2={svgPx}
        y2={svgPy}
        stroke={MEDIAN_COLOR}
        strokeWidth={1.5}
        strokeDasharray="5 3"
        opacity={0.7}
        data-testid="median-prediction-line"
      />

      {/* ── Lines from predicted candidate to each elected winner ── */}
      {winnerA &&
        (() => {
          const wa = candidates.find((c) => c.name === winnerA);
          if (!wa) return null;
          return (
            <line
              x1={svgMx}
              y1={svgMy}
              x2={domainToSvgX(wa.x)}
              y2={domainToSvgY(wa.y)}
              stroke={colorA}
              strokeWidth={2}
              strokeDasharray={matchA ? undefined : '3 2'}
              opacity={0.8}
              data-testid={matchA ? 'median-match-line' : 'median-miss-line'}
            />
          );
        })()}

      {winnerB &&
        winnerB !== winnerA &&
        (() => {
          const wb = candidates.find((c) => c.name === winnerB);
          if (!wb) return null;
          return (
            <line
              x1={svgMx}
              y1={svgMy}
              x2={domainToSvgX(wb.x)}
              y2={domainToSvgY(wb.y)}
              stroke={colorB}
              strokeWidth={2}
              strokeDasharray={matchB ? undefined : '3 2'}
              opacity={0.8}
            />
          );
        })()}

      {/* ── Pulsing halo ── */}
      <circle
        cx={svgMx}
        cy={svgMy}
        r={16}
        fill={MEDIAN_COLOR}
        fillOpacity={0.08}
        stroke={MEDIAN_COLOR}
        strokeWidth={1}
        strokeOpacity={0.3}
        data-testid="median-halo"
      >
        <animate attributeName="r" values="12;20;12" dur="2s" repeatCount="indefinite" />
        <animate
          attributeName="fill-opacity"
          values="0.12;0.04;0.12"
          dur="2s"
          repeatCount="indefinite"
        />
      </circle>

      {/* ── Cross ✛ ── */}
      <g data-testid="median-cross">
        <line
          x1={svgMx - crossSize}
          y1={svgMy}
          x2={svgMx + crossSize}
          y2={svgMy}
          stroke={MEDIAN_COLOR}
          strokeWidth={2.5}
        />
        <line
          x1={svgMx}
          y1={svgMy - crossSize}
          x2={svgMx}
          y2={svgMy + crossSize}
          stroke={MEDIAN_COLOR}
          strokeWidth={2.5}
        />
      </g>

      {/* ── Label ── */}
      <text
        x={svgMx + crossSize + 4}
        y={svgMy - 4}
        fontSize={10}
        fill={MEDIAN_COLOR}
        fontWeight={600}
        stroke="#fff"
        strokeWidth={2.5}
        paintOrder="stroke"
        data-testid="median-label"
      >
        {t('ideologyMap.medianVoter')}
      </text>

      {/* ── Predicted candidate badge ── */}
      <g transform={`translate(${svgPx}, ${svgPy - 30})`}>
        <rect
          x={-45}
          y={-10}
          width={90}
          height={18}
          rx={4}
          fill={MEDIAN_COLOR}
          fillOpacity={0.12}
          stroke={MEDIAN_COLOR}
          strokeWidth={0.8}
        />
        <text textAnchor="middle" y={2} fontSize={9} fill={MEDIAN_COLOR} fontWeight={600}>
          {t('ideologyMap.medianPredicts')}: {predicted.name}
        </text>
      </g>

      {/* ── Miss label when both methods diverge ── */}
      {winnerA && !matchA && (
        <text
          x={svgMx}
          y={svgMy + crossSize + 16}
          textAnchor="middle"
          fontSize={9}
          fill={MISS_COLOR}
          stroke="#fff"
          strokeWidth={2}
          paintOrder="stroke"
          data-testid="median-miss-label"
        >
          {methodA} {t('ideologyMap.medianMiss')}
        </text>
      )}
    </g>
  );
};

export default MedianVoterLayer;

// ── Legend component (outside the SVG) ───────────────────────────────────────

export const MedianVoterLegend: React.FC<{
  voters: MedianVoterPoint[];
  candidates: MedianCandidate[];
  winnerA: string | null;
  winnerB: string | null;
  methodA: string;
  methodB: string;
}> = ({ voters, candidates, winnerA, winnerB, methodA, methodB }) => {
  const { t } = useTranslation();

  const { mx, predicted } = useMemo(() => {
    if (voters.length === 0 || candidates.length === 0) return { mx: 0, predicted: null };
    const mxVal = computeMedian(voters.map((v) => v.x));
    const myVal = computeMedian(voters.map((v) => v.y));
    return { mx: mxVal, predicted: nearestCandidate(mxVal, myVal, candidates) };
  }, [voters, candidates]);

  if (!predicted) return null;

  const matchA = winnerA === predicted.name;
  const matchB = winnerB === predicted.name;

  return (
    <div
      className="rounded p-2 mt-2"
      style={{
        background: '#fff8f0',
        border: '1px solid #e67e22',
        fontSize: '0.78rem',
      }}
      data-testid="median-legend"
    >
      <div className="flex flex-wrap gap-3">
        <span>
          <span style={{ color: MEDIAN_COLOR, fontWeight: 600 }}>
            ✛ {t('ideologyMap.medianVoter')}
          </span>{' '}
          x={mx.toFixed(2)}
        </span>
        <span>
          <strong>
            {t('ideologyMap.medianPredicts')}: {predicted.name}
          </strong>
        </span>
        {winnerA && (
          <span style={{ color: matchA ? HIT_COLOR : MISS_COLOR }}>
            {methodA}: {winnerA}{' '}
            {matchA
              ? '✓'
              : `✗ (±${Math.abs((candidates.find((c) => c.name === winnerA)?.x ?? 0) - mx).toFixed(
                  2
                )})`}
          </span>
        )}
        {winnerB && winnerB !== winnerA && (
          <span style={{ color: matchB ? HIT_COLOR : MISS_COLOR }}>
            {methodB}: {winnerB} {matchB ? '✓' : `✗`}
          </span>
        )}
      </div>
    </div>
  );
};
