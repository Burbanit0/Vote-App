/**
 * QuadraticBudgetViz — Visualises how credits are distributed in a QV election.
 *
 * Shows:
 *   1. Stacked bar chart: average credits spent per candidate
 *   2. "Budget moyen par candidat" stat
 *   3. "Indice de Gini des crédits" (0 = equal, 1 = all on one candidate)
 */
import React, { useMemo } from 'react';
import { Badge } from '@/components/ui/badge';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { CHART_COLORS_LIGHT } from '../../constants/chartColors';

// ── Gini coefficient (client-side mirror of the Python implementation) ─────

function gini(values: number[]): number {
  const n = values.length;
  if (n < 2) return 0;
  const total = values.reduce((a, b) => a + b, 0);
  if (total <= 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const weighted = sorted.reduce((acc, v, i) => acc + (i + 1) * v, 0);
  return Math.max(
    0,
    Math.min(1, parseFloat(((2 * weighted) / (n * total) - (n + 1) / n).toFixed(3)))
  );
}

// ── Types ─────────────────────────────────────────────────────────────────────

interface Props {
  /** { [candidateName]: average credits spent by each voter on this candidate } */
  creditDistribution: Record<string, number>;
  /** Average total credits spent per voter */
  totalCreditsUsed: number;
  /** Budget per voter (default 100) */
  budget?: number;
  /** QV vote scores { [candidate]: totalVotes } */
  scores?: Record<string, number>;
}

// ── Custom tooltip ─────────────────────────────────────────────────────────────

function QVTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const entry = payload[0];
  return (
    <div
      style={{
        background: 'var(--bs-body-bg, white)',
        border: '1px solid var(--bs-border-color, #dee2e6)',
        borderRadius: 8,
        padding: '8px 12px',
        fontSize: '0.82rem',
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
      }}
    >
      <div className="font-bold mb-1">{entry.payload.candidate}</div>
      <div>
        Crédits moyens : <strong>{entry.value?.toFixed(1)}</strong>
      </div>
      {entry.payload.votes != null && (
        <div className="text-muted-foreground">
          Votes QV totaux : {entry.payload.votes.toFixed(0)}
        </div>
      )}
    </div>
  );
}

// ── QuadraticBudgetViz ────────────────────────────────────────────────────────

const QuadraticBudgetViz: React.FC<Props> = ({
  creditDistribution,
  totalCreditsUsed,
  budget = 100,
  scores,
}) => {
  const candidates = Object.keys(creditDistribution);

  const chartData = useMemo(
    () =>
      candidates
        .map((c, i) => ({
          candidate: c,
          credits: parseFloat((creditDistribution[c] ?? 0).toFixed(1)),
          votes: scores?.[c],
          fill: CHART_COLORS_LIGHT[i % CHART_COLORS_LIGHT.length],
        }))
        .sort((a, b) => b.credits - a.credits),
    [creditDistribution, candidates, scores]
  );

  const creditValues = candidates.map((c) => creditDistribution[c] ?? 0);
  const giniIndex = gini(creditValues);
  const avgPerCand = totalCreditsUsed / Math.max(1, candidates.length);
  const unused = Math.max(0, budget - totalCreditsUsed);

  // Gini label colour
  const giniColor = giniIndex < 0.3 ? '#1b5e20' : giniIndex < 0.6 ? '#b35c00' : '#b71c1c';

  return (
    <Card className="mt-3 mb-0">
      <CardHeader className="block space-y-0 border-b border-border px-4 py-2 py-2">
        <strong>💎 Répartition des crédits (Vote Quadratique)</strong>
        <span className="text-muted-foreground ms-2" style={{ fontSize: '0.82rem' }}>
          — budget de {budget} crédits par électeur
        </span>
      </CardHeader>
      <CardBody>
        {/* ── Summary stats ── */}
        <div className="flex gap-4 mb-3 flex-wrap" style={{ fontSize: '0.85rem' }}>
          <div>
            <span className="text-muted-foreground">Crédits utilisés en moy. :</span>{' '}
            <strong>
              {totalCreditsUsed.toFixed(1)} / {budget}
            </strong>
          </div>
          <div>
            <span className="text-muted-foreground">Budget moy. / candidat :</span>{' '}
            <strong>{avgPerCand.toFixed(1)}</strong>
          </div>
          <div>
            <span className="text-muted-foreground">Crédits non utilisés :</span>{' '}
            <strong>{unused.toFixed(1)}</strong>
            {unused > 5 && (
              <Badge variant="warning" className="ms-1" style={{ fontSize: '0.7rem' }}>
                budget non épuisé
              </Badge>
            )}
          </div>
          <div>
            <span className="text-muted-foreground">Indice de Gini :</span>{' '}
            <strong style={{ color: giniColor }}>{giniIndex.toFixed(3)}</strong>
            <span className="text-muted-foreground ms-1" style={{ fontSize: '0.78rem' }}>
              (
              {giniIndex < 0.3
                ? 'faible concentration'
                : giniIndex < 0.6
                  ? 'concentration modérée'
                  : 'forte concentration'}
              )
            </span>
          </div>
        </div>

        {/* ── Bar chart ── */}
        <ResponsiveContainer width="100%" height={Math.max(100, candidates.length * 42 + 40)}>
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ top: 4, right: 60, left: 0, bottom: 4 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              horizontal={false}
              stroke="var(--bs-border-color, #dee2e6)"
            />
            <XAxis
              type="number"
              domain={[0, budget]}
              tickFormatter={(v) => `${v}`}
              label={{
                value: 'Crédits moyens',
                position: 'insideBottom',
                offset: -4,
                fontSize: 11,
              }}
              tick={{ fontSize: 11 }}
            />
            <YAxis type="category" dataKey="candidate" width={72} tick={{ fontSize: 12 }} />
            <Tooltip content={<QVTooltip />} />
            <Bar dataKey="credits" radius={[0, 4, 4, 0]} maxBarSize={28}>
              {chartData.map((entry) => (
                <Cell key={entry.candidate} fill={entry.fill} />
              ))}
              <LabelList
                dataKey="credits"
                position="right"
                formatter={(v: unknown) => (typeof v === 'number' ? `${v.toFixed(0)} cr.` : '')}
                style={{ fontSize: '0.8rem', fill: 'var(--bs-body-color, #333)' }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>

        {/* ── Pedagogical note ── */}
        <div
          className="text-muted-foreground mt-2"
          style={{ fontSize: '0.78rem', lineHeight: 1.5 }}
        >
          <strong>Comment lire ce graphique :</strong> chaque barre représente les crédits moyens
          qu'un électeur consacre à ce candidat. Un vote coûte v² crédits — obtenir 3 votes coûte 9
          crédits, pas 3. Un indice de Gini élevé signifie que les crédits sont concentrés sur un
          seul candidat (forte intensité des préférences).
        </div>
      </CardBody>
    </Card>
  );
};

export default QuadraticBudgetViz;
