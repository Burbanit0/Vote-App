/**
 * MajorityJudgmentChart — stacked horizontal bar chart for MJ grade distributions.
 *
 * Each row = one candidate.
 * Each segment = one grade (À Rejeter → Excellent), colour: red → green.
 * A vertical line marks the median grade position.
 * Candidates sorted by median grade (descending); winner shown first.
 */
import React, { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Badge } from 'react-bootstrap';

// ── Grade palette (red → orange → yellow → light-green → green → dark-green) ──

export const MJ_GRADE_KEYS = [
  'mj.àRejeter',
  'mj.passable',
  'mj.assezBien',
  'mj.bien',
  'mj.trèsBien',
  'mj.excellent',
] as const;

const MJ_COLORS = [
  '#dc3545',   // À Rejeter  — red
  '#e67e22',   // Passable   — orange
  '#f0c040',   // Assez Bien — amber
  '#5cb85c',   // Bien       — light green
  '#007A33',   // Très Bien  — green
  '#004d1f',   // Excellent  — dark green
];

// ── Types ─────────────────────────────────────────────────────────────────────

export interface MJGradeDistribution {
  [gradeName: string]: number;   // grade label → count
}

export interface MJResult {
  winner:              string | null;
  grades:              Record<string, MJGradeDistribution>;
  medians:             Record<string, string>;
  scores:              Record<string, number>;
  grade_distributions: Record<string, number[]>;  // candidate → [count_g0 … count_g5]
}

// ── SVG layout ────────────────────────────────────────────────────────────────

const ROW_H    = 36;
const LABEL_W  = 100;
const BAR_W    = 380;
const PAD_TOP  = 4;
const SVG_W    = LABEL_W + BAR_W + 8;

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Grade index (0-5) for a given grade label string. */
export function gradeIndex(
  gradeLabel: string,
  allLabels:  string[],
): number {
  const i = allLabels.indexOf(gradeLabel);
  return i >= 0 ? i : 0;
}

/** Compute the x-pixel position of the median line within the bar area. */
export function medianLineX(
  dist:      number[],
  gradeIdx:  number,
  barWidth:  number,
): number {
  const total = dist.reduce((a, b) => a + b, 0) || 1;
  // Sum of fractions for grades below median + half of median grade
  const below  = dist.slice(0, gradeIdx).reduce((a, b) => a + b, 0);
  const atMed  = dist[gradeIdx] ?? 0;
  const x      = ((below + atMed / 2) / total) * barWidth;
  return Math.round(x);
}

// ── Component ─────────────────────────────────────────────────────────────────

export interface MajorityJudgmentChartProps {
  mjResult:   MJResult;
  /** All candidate names in this election (for ordering). */
  candidates: string[];
}

const MajorityJudgmentChart: React.FC<MajorityJudgmentChartProps> = ({
  mjResult,
  candidates,
}) => {
  const { t } = useTranslation();

  const gradeLabels = MJ_GRADE_KEYS.map((k) => t(k));

  // Sort candidates: winner first, then by score descending
  const sorted = useMemo(() => {
    return [...candidates]
      .filter((c) => mjResult.grade_distributions?.[c])
      .sort((a, b) => {
        if (a === mjResult.winner) return -1;
        if (b === mjResult.winner) return 1;
        return (mjResult.scores[b] ?? 0) - (mjResult.scores[a] ?? 0);
      });
  }, [candidates, mjResult]);

  if (sorted.length === 0) return null;

  const svgH = sorted.length * ROW_H + PAD_TOP * 2 + 20;

  return (
    <div data-testid="mj-chart">
      {/* Winner badge */}
      {mjResult.winner && (
        <div className="d-flex align-items-center gap-2 mb-2">
          <Badge bg="success" style={{ fontSize: '0.78rem' }} data-testid="mj-winner-badge">
            🏆 {t('mj.winner')}: {mjResult.winner}
          </Badge>
          <span className="text-muted" style={{ fontSize: '0.75rem' }}>
            {t('mj.median')}: <strong>{mjResult.medians[mjResult.winner] ?? '—'}</strong>
          </span>
        </div>
      )}

      <svg
        viewBox={`0 0 ${SVG_W} ${svgH}`}
        width="100%"
        style={{ display: 'block', overflow: 'visible' }}
        aria-label={t('mj.chartAriaLabel')}
      >
        {sorted.map((cand, rowIdx) => {
          const dist     = mjResult.grade_distributions[cand] ?? [];
          const total    = dist.reduce((a, b) => a + b, 0) || 1;
          const medLabel = mjResult.medians[cand] ?? '';
          const medIdx   = gradeIndex(medLabel, gradeLabels);
          const medX     = medianLineX(dist, medIdx, BAR_W);
          const y        = PAD_TOP + rowIdx * ROW_H;
          const isWinner = cand === mjResult.winner;

          // Build segments
          let xCursor = 0;
          const segments = dist.map((count, gi) => {
            const w = Math.round((count / total) * BAR_W);
            const seg = { x: xCursor, w, gi, count };
            xCursor += w;
            return seg;
          });

          return (
            <g key={cand} data-testid={`mj-row-${cand}`}>
              {/* Candidate label */}
              <text
                x={LABEL_W - 6}
                y={y + ROW_H / 2}
                textAnchor="end"
                dominantBaseline="central"
                fontSize={isWinner ? 11 : 10}
                fontWeight={isWinner ? 700 : 400}
                fill={isWinner ? '#007A33' : 'currentColor'}
              >
                {isWinner ? '🏆 ' : ''}{cand}
              </text>

              {/* Grade segments */}
              {segments.map(({ x, w, gi, count }) => {
                if (w === 0) return null;
                const pct = Math.round((count / total) * 100);
                return (
                  <rect
                    key={gi}
                    x={LABEL_W + x}
                    y={y + 6}
                    width={w}
                    height={ROW_H - 12}
                    fill={MJ_COLORS[gi]}
                    rx={gi === 0 ? 3 : 0}
                    style={{ transition: 'width 0.4s ease' }}
                    data-testid="mj-grade-segment"
                  >
                    <title>
                      {cand} — {gradeLabels[gi]}: {pct}%
                    </title>
                  </rect>
                );
              })}

              {/* Median line */}
              <line
                x1={LABEL_W + medX}
                y1={y + 2}
                x2={LABEL_W + medX}
                y2={y + ROW_H - 2}
                stroke="#212529"
                strokeWidth={2.5}
                strokeDasharray="none"
                data-testid="mj-median-line"
              />
              {/* Median label above the line */}
              <text
                x={LABEL_W + medX}
                y={y}
                textAnchor="middle"
                fontSize={8}
                fill="#212529"
                fontWeight={600}
              >
                {medLabel}
              </text>
            </g>
          );
        })}

        {/* Grade legend axis at the bottom */}
        {[0, 1, 2, 3, 4, 5].map((gi) => (
          <g key={gi}>
            <rect
              x={LABEL_W + gi * (BAR_W / 6)}
              y={svgH - 14}
              width={BAR_W / 6 - 1}
              height={8}
              fill={MJ_COLORS[gi]}
              rx={2}
            />
            <text
              x={LABEL_W + gi * (BAR_W / 6) + BAR_W / 12}
              y={svgH - 1}
              textAnchor="middle"
              fontSize={7}
              fill="#6c757d"
            >
              {gradeLabels[gi]}
            </text>
          </g>
        ))}
      </svg>

      {/* Tooltip hint */}
      <div className="text-muted mt-1" style={{ fontSize: '0.72rem' }}>
        — {t('mj.medianLineHint')}
      </div>
    </div>
  );
};

export default MajorityJudgmentChart;
