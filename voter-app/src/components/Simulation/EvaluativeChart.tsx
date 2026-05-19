/**
 * EvaluativeChart — stacked horizontal bar chart for evaluative voting (+1/0/−1).
 *
 * Each row = one candidate, sorted by net score descending.
 * Segments: green (+1 approvals) · grey (0 neutral) · red (−1 rejections).
 * Vertical line at the zero-axis separates approvals from rejections.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { Badge } from 'react-bootstrap';

// ── Types ─────────────────────────────────────────────────────────────────────

export interface EvaluativeDistribution {
  '+1': number;
  '0':  number;
  '-1': number;
}

export interface EvaluativeResult {
  winner:       string | null;
  scores:       Record<string, number>;
  ev_distribution: Record<string, EvaluativeDistribution>;
}

// ── SVG layout ────────────────────────────────────────────────────────────────

const ROW_H    = 32;
const LABEL_W  = 100;
const BAR_W    = 380;
const PAD_V    = 4;

// ── Component ─────────────────────────────────────────────────────────────────

export interface EvaluativeChartProps {
  evResult:   EvaluativeResult;
  candidates: string[];
}

const EvaluativeChart: React.FC<EvaluativeChartProps> = ({ evResult, candidates }) => {
  const { t } = useTranslation();

  const sorted = [...candidates]
    .filter(c => evResult.ev_distribution?.[c])
    .sort((a, b) => {
      if (a === evResult.winner) return -1;
      if (b === evResult.winner) return 1;
      return (evResult.scores[b] ?? 0) - (evResult.scores[a] ?? 0);
    });

  if (sorted.length === 0) return null;

  const totalVoters = Object.values(evResult.ev_distribution[sorted[0]] ?? {}).reduce(
    (s, v) => s + v, 0
  ) || 1;

  const svgH = sorted.length * ROW_H + PAD_V * 2 + 24;

  // Max absolute score for proportional bar widths
  const maxAbs = Math.max(
    ...sorted.map(c => Math.abs(evResult.scores[c] ?? 0)),
    1,
  );

  return (
    <div data-testid="evaluative-chart">
      {/* Winner badge */}
      {evResult.winner && (
        <div className="d-flex align-items-center gap-2 mb-2">
          <Badge bg="success" style={{ fontSize: '0.78rem' }} data-testid="ev-winner-badge">
            🏆 {t('ev.winner')}: {evResult.winner}
            {' '}
            <span style={{ fontWeight: 400 }}>
              ({evResult.scores[evResult.winner] >= 0 ? '+' : ''}{evResult.scores[evResult.winner]})
            </span>
          </Badge>
        </div>
      )}

      <svg
        data-testid="ev-svg"
        viewBox={`0 0 ${LABEL_W + BAR_W + 60} ${svgH}`}
        width="100%"
        style={{ display: 'block', overflow: 'visible' }}
        aria-label={t('ev.chartAriaLabel')}
      >
        {/* Column headers */}
        <text x={LABEL_W + BAR_W / 2} y={14} textAnchor="middle"
          fontSize={8} fill="#6c757d">
          {t('ev.axisLabel')}
        </text>

        {/* Zero axis */}
        <line
          x1={LABEL_W + BAR_W / 2} y1={PAD_V + 16}
          x2={LABEL_W + BAR_W / 2} y2={svgH - 20}
          stroke="#adb5bd" strokeWidth={1} strokeDasharray="3 2"
        />

        {/* Rows */}
        {sorted.map((cand, ri) => {
          const dist  = evResult.ev_distribution[cand] ?? { '+1': 0, '0': 0, '-1': 0 };
          const score = evResult.scores[cand] ?? 0;
          const isWinner = cand === evResult.winner;

          const pctApprove = dist['+1']  / totalVoters;
          const pctNeutral = dist['0']   / totalVoters;
          const pctReject  = dist['-1']  / totalVoters;

          // Bars extend from the centre outward
          const approveW  = Math.round(pctApprove * BAR_W / 2);
          const neutralWL = Math.round(pctNeutral * BAR_W / 4);  // half left of zero
          const neutralWR = Math.round(pctNeutral * BAR_W / 4);  // half right of zero
          const rejectW   = Math.round(pctReject  * BAR_W / 2);

          const y = PAD_V + 16 + ri * ROW_H;
          const cx = LABEL_W + BAR_W / 2;  // centre = zero axis

          return (
            <g key={cand} data-testid={`ev-row-${cand}`}>
              {/* Candidate label */}
              <text
                x={LABEL_W - 6} y={y + ROW_H / 2}
                textAnchor="end" dominantBaseline="central"
                fontSize={10} fontWeight={isWinner ? 700 : 400}
                fill={isWinner ? '#007A33' : 'currentColor'}
              >
                {isWinner ? '🏆 ' : ''}{cand}
              </text>

              {/* Track background */}
              <rect x={LABEL_W} y={y + 6} width={BAR_W} height={ROW_H - 12}
                rx={3} fill="#f8f9fa" />

              {/* Approval bar (right of centre) */}
              {approveW > 0 && (
                <rect
                  x={cx} y={y + 6}
                  width={approveW} height={ROW_H - 12}
                  fill="#28a745" rx={0}
                  data-testid="ev-approve-bar"
                  style={{ transition: 'width 0.4s ease' }}
                >
                  <title>{cand}: +{dist['+1']} approvals ({Math.round(pctApprove * 100)}%)</title>
                </rect>
              )}

              {/* Neutral bars (split around centre) */}
              {neutralWL > 0 && (
                <rect x={cx - neutralWL} y={y + 6}
                  width={neutralWL} height={ROW_H - 12}
                  fill="#adb5bd" opacity={0.5}
                  data-testid="ev-neutral-bar"
                />
              )}
              {neutralWR > 0 && (
                <rect x={cx + approveW} y={y + 6}
                  width={neutralWR} height={ROW_H - 12}
                  fill="#adb5bd" opacity={0.5}
                />
              )}

              {/* Rejection bar (left of centre) */}
              {rejectW > 0 && (
                <rect
                  x={cx - neutralWL - rejectW} y={y + 6}
                  width={rejectW} height={ROW_H - 12}
                  fill="#dc3545" rx={0}
                  data-testid="ev-reject-bar"
                  style={{ transition: 'width 0.4s ease' }}
                >
                  <title>{cand}: −{dist['-1']} rejections ({Math.round(pctReject * 100)}%)</title>
                </rect>
              )}

              {/* Net score label */}
              <text
                x={LABEL_W + BAR_W + 6} y={y + ROW_H / 2}
                dominantBaseline="central" fontSize={9}
                fill={score > 0 ? '#28a745' : score < 0 ? '#dc3545' : '#6c757d'}
                fontWeight={isWinner ? 700 : 400}
              >
                {score >= 0 ? '+' : ''}{score}
              </text>
            </g>
          );
        })}

        {/* Legend */}
        <g transform={`translate(${LABEL_W}, ${svgH - 18})`}>
          <rect x={0}   y={0} width={12} height={10} rx={2} fill="#28a745" />
          <text x={16}  y={8} fontSize={8} fill="#6c757d">+1 {t('ev.approve')}</text>
          <rect x={80}  y={0} width={12} height={10} rx={2} fill="#adb5bd" opacity={0.6} />
          <text x={96}  y={8} fontSize={8} fill="#6c757d">0 {t('ev.neutral')}</text>
          <rect x={155} y={0} width={12} height={10} rx={2} fill="#dc3545" />
          <text x={171} y={8} fontSize={8} fill="#6c757d">−1 {t('ev.reject')}</text>
        </g>
      </svg>

      <div className="text-muted mt-1" style={{ fontSize: '0.72rem' }}>
        {t('ev.hint')}
      </div>
    </div>
  );
};

export default EvaluativeChart;
