import React, { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Cell, Pie, PieChart, Tooltip } from 'recharts';
import { useTranslation } from 'react-i18next';
import { MethodGroup } from '../../services/electionApi';

// ── Palette ───────────────────────────────────────────────────────────────────

const DONUT_COLORS = [
  '#005CAB',
  '#C8590A',
  '#007A33',
  '#7B2D8B',
  '#9C3A00',
  '#005f73',
  '#B71C1C',
  '#2A9D8F',
];

// ── Custom tooltip ────────────────────────────────────────────────────────────

const DonutTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const { winner, methods, pct } = payload[0].payload as MethodGroup;
  return (
    <div
      className="rounded p-2"
      style={{
        background: 'var(--bs-body-bg)',
        border: '1px solid var(--bs-border-color)',
        fontSize: '0.74rem',
        maxWidth: 200,
      }}
    >
      <strong>{winner}</strong>{' '}
      <span className="text-muted-foreground">
        ({methods.length} {methods.length === 1 ? 'méthode' : 'méthodes'} — {Math.round(pct * 100)}
        %)
      </span>
      <div className="text-muted-foreground mt-1">{methods.join(' · ')}</div>
    </div>
  );
};

// ── Centre label (rendered via SVG foreignObject trick with a custom label) ──

const CentreLabel = ({
  cx,
  cy,
  singleGroup,
  winner,
  total,
  t,
}: {
  cx: number;
  cy: number;
  singleGroup: boolean;
  winner?: string;
  total: number;
  t: (k: string, o?: Record<string, unknown>) => string;
}) => (
  <text x={cx} y={cy} textAnchor="middle" dominantBaseline="central">
    {singleGroup ? (
      <>
        <tspan fontSize={18} fill="#007A33">
          ✓
        </tspan>
      </>
    ) : (
      <>
        <tspan fontSize={11} fill="var(--bs-secondary-color, #6c757d)" dy="-5">
          {total}
        </tspan>
        <tspan fontSize={9} fill="var(--bs-secondary-color, #6c757d)" x={cx} dy={14}>
          {t('insight.donutCenter')}
        </tspan>
      </>
    )}
  </text>
);

// ── Props ─────────────────────────────────────────────────────────────────────

interface Props {
  methodGroups: MethodGroup[];
  totalMethods: number;
}

// ── Component ─────────────────────────────────────────────────────────────────

const MethodGroupDonut: React.FC<Props> = ({ methodGroups, totalMethods }) => {
  const { t } = useTranslation();
  const [highlightedWinner, setHighlightedWinner] = useState<string | null>(null);

  if (methodGroups.length === 0) return null;

  const single = methodGroups.length === 1;
  const singleGroup = methodGroups[0];

  // ── Single-group (full consensus) case ─────────────────────────────────
  if (single) {
    const color = DONUT_COLORS[0];
    return (
      <div className="flex items-center gap-3">
        {/* Donut — full sector */}
        <PieChart width={130} height={130}>
          <Pie
            data={[{ ...singleGroup, value: 1 }]}
            cx={60}
            cy={60}
            innerRadius={38}
            outerRadius={60}
            dataKey="value"
            isAnimationActive
            animationDuration={600}
          >
            <Cell fill={color} />
          </Pie>
          <CentreLabel
            cx={60}
            cy={60}
            singleGroup={true}
            winner={singleGroup.winner}
            total={totalMethods}
            t={t}
          />
        </PieChart>

        {/* Single-group info */}
        <div>
          <div className="font-semibold" style={{ fontSize: '0.85rem', color }}>
            {singleGroup.winner}
          </div>
          <div className="text-muted-foreground" style={{ fontSize: '0.75rem' }}>
            {t('insight.donutSingle', { total: totalMethods })}
          </div>
        </div>
      </div>
    );
  }

  // ── Multi-group case ───────────────────────────────────────────────────
  const pieData = methodGroups.map((g) => ({ ...g, value: g.pct }));

  const highlightedGroup = highlightedWinner
    ? methodGroups.find((g) => g.winner === highlightedWinner)
    : null;

  return (
    <div className="flex items-start gap-3" style={{ minWidth: 0 }}>
      {/* Donut chart */}
      <div style={{ flexShrink: 0 }}>
        <PieChart width={140} height={140}>
          <Pie
            data={pieData}
            cx={66}
            cy={66}
            innerRadius={40}
            outerRadius={62}
            dataKey="value"
            isAnimationActive
            animationDuration={700}
            strokeWidth={0}
            onMouseEnter={(_, index) => setHighlightedWinner(pieData[index]?.winner ?? null)}
            onMouseLeave={() => setHighlightedWinner(null)}
          >
            {pieData.map((entry, idx) => (
              <Cell
                key={entry.winner}
                fill={DONUT_COLORS[idx % DONUT_COLORS.length]}
                opacity={
                  highlightedWinner === null || highlightedWinner === entry.winner ? 1 : 0.35
                }
                style={{ transition: 'opacity 0.2s', cursor: 'pointer' }}
                onClick={() =>
                  setHighlightedWinner(highlightedWinner === entry.winner ? null : entry.winner)
                }
              />
            ))}
          </Pie>
          <Tooltip content={<DonutTooltip />} />
          <CentreLabel cx={66} cy={66} singleGroup={false} total={totalMethods} t={t} />
        </PieChart>
      </div>

      {/* Legend */}
      <div style={{ flex: 1, minWidth: 0 }}>
        {methodGroups.map((group, idx) => {
          const color = DONUT_COLORS[idx % DONUT_COLORS.length];
          const isHighlight = highlightedWinner === group.winner;
          const dimmed = highlightedWinner !== null && !isHighlight;

          return (
            <div
              key={group.winner}
              className="flex items-center gap-2 mb-1"
              style={{ cursor: 'pointer', opacity: dimmed ? 0.4 : 1, transition: 'opacity 0.2s' }}
              onClick={() =>
                setHighlightedWinner(highlightedWinner === group.winner ? null : group.winner)
              }
            >
              <span
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: '50%',
                  background: color,
                  display: 'inline-block',
                  flexShrink: 0,
                }}
              />
              <span className="font-semibold" style={{ fontSize: '0.8rem', color }}>
                {group.winner}
              </span>
              <span className="text-muted-foreground" style={{ fontSize: '0.72rem' }}>
                {group.methods.length}/{totalMethods}
              </span>
            </div>
          );
        })}

        {/* Expanded method list for highlighted group */}
        {highlightedGroup && (
          <div className="mt-1 flex flex-wrap gap-1">
            {highlightedGroup.methods.map((m) => {
              const idx = methodGroups.findIndex((g) => g.winner === highlightedGroup.winner);
              return (
                <Badge
                  key={m}
                  style={{
                    background: DONUT_COLORS[idx % DONUT_COLORS.length],
                    fontSize: '0.64rem',
                    opacity: 0.85,
                  }}
                >
                  {m}
                </Badge>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default MethodGroupDonut;
