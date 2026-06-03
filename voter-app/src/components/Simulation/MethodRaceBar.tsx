/**
 * MethodRaceBar — animated SVG horizontal-bar race for voting methods.
 *
 * Metric shown: stability = winner_distribution[most_common_winner]
 * (fraction of simulations where the method elected its most frequent winner).
 *
 * Animation model:
 *   - Bars extend via CSS `width` transition (0.3s) on each <rect>
 *   - Rows reorder via CSS `transform: translateY` (0.4s) on each <g>
 *   - Both use the same DOM element across renders (keyed by method name)
 *     so React reuses the node and the browser's CSS engine interpolates.
 */
import React, { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Badge } from '@/components/ui/badge';
import { MethodStreamStats } from '../../hooks/useMonteCarloStream';

// ── Constants ─────────────────────────────────────────────────────────────────

const ROW_H          = 36;
const LABEL_W        = 130;  // left label column
const RIGHT_LABEL_W  = 120;  // right label column
const H_PADDING      = 12;
const SVG_INNER_W    = 480;  // bar area width
const TOTAL_W        = LABEL_W + SVG_INNER_W + RIGHT_LABEL_W + H_PADDING * 2;
const STABILITY_LINE = 0.5;
const BADGE_THRESHOLD = 0.8;

// Candidate colour palette (matches RACE_COLORS in MonteCarloRaceChart)
const CAND_COLORS = [
  '#1a56cc', '#b35c00', '#b71c1c', '#006957',
  '#1b5e20', '#544200', '#7B2D8B', '#005f73',
  '#b35c00', '#2A9D8F', '#9C3A00', '#264653',
];

function candidateColor(name: string, allCandidates: string[]): string {
  const idx = allCandidates.indexOf(name);
  return idx >= 0 ? CAND_COLORS[idx % CAND_COLORS.length] : '#6c757d';
}

// ── Types ─────────────────────────────────────────────────────────────────────

export interface MethodRow {
  method:      string;
  winner:      string | null;
  stability:   number;   // [0, 1]
  rank:        number;   // 0 = most stable
}

/** Pure sort function — exported for testing. */
export function sortMethods(
  partialResults: Record<string, MethodStreamStats>,
): MethodRow[] {
  return Object.entries(partialResults)
    .map(([method, stats]) => {
      const winner    = stats.most_common_winner;
      const stability = winner ? (stats.winner_distribution[winner] ?? 0) : 0;
      return { method, winner, stability, rank: 0 };
    })
    .sort((a, b) => b.stability - a.stability)
    .map((row, i) => ({ ...row, rank: i }));
}

// ── Component ─────────────────────────────────────────────────────────────────

interface Props {
  partialResults: Record<string, MethodStreamStats>;
  isRunning:      boolean;
}

const MethodRaceBar: React.FC<Props> = ({ partialResults, isRunning }) => {
  const { t } = useTranslation();

  const rows = useMemo(() => sortMethods(partialResults), [partialResults]);

  // Collect all candidate names for consistent colour mapping
  const allCandidates = useMemo(() => {
    const names = new Set<string>();
    for (const s of Object.values(partialResults)) {
      if (s.most_common_winner) names.add(s.most_common_winner);
      for (const c of Object.keys(s.winner_distribution)) names.add(c);
    }
    return [...names].sort();
  }, [partialResults]);

  const svgH     = Math.max(40, rows.length * ROW_H + 20);
  const barMaxW  = SVG_INNER_W - 8;

  // Methods that crossed the badge threshold
  const stableLeaders = useMemo(
    () => rows.filter((r) => r.stability >= BADGE_THRESHOLD),
    [rows],
  );

  if (rows.length === 0) return null;

  return (
    <div>
      {/* Header badges */}
      {!isRunning && stableLeaders.length > 0 && (
        <div className="d-flex flex-wrap gap-2 mb-2">
          {stableLeaders.map((r) => (
            <Badge
              key={r.method}
              style={{ background: candidateColor(r.winner ?? '', allCandidates), fontSize: '0.72rem' }}
              data-testid={`stable-badge-${r.method}`}
            >
              🏆 {r.method}: {r.winner} {Math.round(r.stability * 100)}%
            </Badge>
          ))}
        </div>
      )}

      {/* SVG race chart */}
      <svg
        data-testid="method-race-svg"
        viewBox={`0 0 ${TOTAL_W} ${svgH}`}
        width="100%"
        style={{ display: 'block', overflow: 'visible' }}
        aria-label={t('methodRace.ariaLabel')}
      >
        {/* Left label column header */}
        <text x={LABEL_W - 6} y={14} textAnchor="end" fontSize={9} fill="#6c757d">
          {t('common.method')}
        </text>

        {/* 50% reference line */}
        <line
          x1={LABEL_W + H_PADDING + barMaxW * STABILITY_LINE}
          y1={0}
          x2={LABEL_W + H_PADDING + barMaxW * STABILITY_LINE}
          y2={svgH}
          stroke="#dc3545"
          strokeWidth={1}
          strokeDasharray="4 2"
          opacity={0.6}
        />
        <text
          x={LABEL_W + H_PADDING + barMaxW * STABILITY_LINE + 3}
          y={10}
          fontSize={8}
          fill="#dc3545"
          opacity={0.8}
        >
          {t('simulation.raceMajority')}
        </text>

        {/* 80% badge reference line */}
        <line
          x1={LABEL_W + H_PADDING + barMaxW * BADGE_THRESHOLD}
          y1={0}
          x2={LABEL_W + H_PADDING + barMaxW * BADGE_THRESHOLD}
          y2={svgH}
          stroke="#198754"
          strokeWidth={1}
          strokeDasharray="2 3"
          opacity={0.4}
        />

        {/* Method rows — keyed by method name so CSS transitions animate correctly */}
        {rows.map((row) => {
          const barW  = Math.max(0, row.stability * barMaxW);
          const color = candidateColor(row.winner ?? '', allCandidates);
          const y     = row.rank * ROW_H + 16;

          return (
            <g
              key={row.method}
              data-testid="method-bar-row"
              data-method={row.method}
              data-stability={row.stability.toFixed(4)}
              style={{
                transform:  `translateY(${y}px)`,
                transition: 'transform 0.4s ease',
              }}
            >
              {/* Left label */}
              <text
                x={LABEL_W - 6}
                y={ROW_H / 2}
                textAnchor="end"
                dominantBaseline="central"
                fontSize={10}
                fill="currentColor"
                style={{ userSelect: 'none' }}
              >
                {row.method.replace(/_/g, ' ')}
              </text>

              {/* Bar track */}
              <rect
                x={LABEL_W + H_PADDING}
                y={ROW_H / 2 - 9}
                width={barMaxW}
                height={18}
                rx={3}
                fill="#e9ecef"
                data-testid="bar-track"
              />

              {/* Filled bar */}
              <rect
                x={LABEL_W + H_PADDING}
                y={ROW_H / 2 - 9}
                width={barW}
                height={18}
                rx={3}
                fill={color}
                fillOpacity={row.stability >= BADGE_THRESHOLD ? 0.9 : 0.7}
                data-testid="bar-fill"
                data-method={row.method}
                style={{ transition: 'width 0.3s ease, fill-opacity 0.3s' }}
              />

              {/* Right label: winner + stability pct */}
              <text
                x={LABEL_W + H_PADDING + barMaxW + 6}
                y={ROW_H / 2}
                dominantBaseline="central"
                fontSize={9.5}
                fill={color}
                fontWeight={row.stability >= BADGE_THRESHOLD ? 700 : 400}
                style={{ userSelect: 'none' }}
              >
                {row.winner ? `${row.winner} ${Math.round(row.stability * 100)}%` : '—'}
              </text>

              {/* Stability "pulse" ring when crossing 80% */}
              {row.stability >= BADGE_THRESHOLD && (
                <circle
                  cx={LABEL_W + H_PADDING + barW - 4}
                  cy={ROW_H / 2}
                  r={6}
                  fill={color}
                  opacity={0.3}
                />
              )}
            </g>
          );
        })}
      </svg>

      {/* Legend */}
      <div className="d-flex flex-wrap gap-3 mt-1" style={{ fontSize: '0.72rem', color: '#6c757d' }}>
        <span>
          <span style={{ color: '#dc3545' }}>—— </span>
          {t('methodRace.majority50')}
        </span>
        <span>
          <span style={{ color: '#198754' }}>·· </span>
          {t('methodRace.stable80')}
        </span>
        {isRunning && <span className="text-muted">{t('methodRace.liveHint')}</span>}
      </div>
    </div>
  );
};

export default MethodRaceBar;
