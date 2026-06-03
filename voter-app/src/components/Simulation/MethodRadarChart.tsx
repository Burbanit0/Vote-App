import React, { useMemo, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Check } from '@/components/ui/form-controls';
import {
  Legend,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { useTranslation } from 'react-i18next';
import { useExpertMode } from '../../stores/useUIStore';
import { SimulationCompareResult } from '../../types';

// ── Palette ─────────────────────────────────────────────────────────────────

const RADAR_COLORS = [
  '#005CAB', '#C8590A', '#007A33', '#7B2D8B', '#9C3A00',
  '#0077B6', '#B71C1C', '#2A9D8F', '#E9A010', '#6A0DAD',
  '#264653', '#E76F51', '#023E8A', '#4CC9F0',
];

const BEGINNER_METHODS = ['plurality', 'borda', 'irv', 'schulze', 'approval'];

// ── Types ────────────────────────────────────────────────────────────────────

interface Props {
  comparisonResults: SimulationCompareResult[];
  allMethodNames:    string[];
}

interface MethodScores {
  equity:     number | null;  // 1 - bayesian_regret (normalised)
  satisfaction: number | null;
  resistance:   number | null;  // 1 - strategic_vulnerability (normalised)
  condorcet:    number | null;  // fraction of runs where condorcet_consistent=true
  stability:    number | null;  // fraction of runs with most-common winner
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function avg(values: (number | null)[]): number | null {
  const valid = values.filter((v): v is number => v !== null && !isNaN(v));
  return valid.length === 0 ? null : valid.reduce((a, b) => a + b, 0) / valid.length;
}

function minMaxNorm(
  vals: Record<string, number | null>,
  invert = false
): Record<string, number> {
  const entries = Object.entries(vals).filter(([, v]) => v !== null) as [string, number][];
  if (entries.length === 0) return {};
  const values = entries.map(([, v]) => v);
  const min    = Math.min(...values);
  const max    = Math.max(...values);
  const range  = max - min;
  return Object.fromEntries(
    entries.map(([k, v]) => {
      const norm = range === 0 ? 1.0 : (v - min) / range;
      return [k, invert ? 1.0 - norm : norm];
    })
  );
}

// ── Component ────────────────────────────────────────────────────────────────

const MethodRadarChart: React.FC<Props> = ({ comparisonResults, allMethodNames }) => {
  const { t }          = useTranslation();
  const { expertMode } = useExpertMode();

  // In beginner mode only show the 5 canonical methods that exist in data
  const candidateMethods = expertMode
    ? allMethodNames
    : allMethodNames.filter((m) => BEGINNER_METHODS.includes(m));

  // ── Compute raw scores per method ─────────────────────────────────────
  const rawScores = useMemo<Record<string, MethodScores>>(() => {
    const scores: Record<string, MethodScores> = {};
    for (const method of allMethodNames) {
      const regretsRaw  = comparisonResults.map((r) => r.methods[method]?.bayesian_regret ?? null);
      const satisfRaw   = comparisonResults.map((r) => r.methods[method]?.majority_satisfaction ?? null);
      const vulnRaw     = comparisonResults.map((r) => r.methods[method]?.strategic_vulnerability ?? null);
      const condorcetVals = comparisonResults.map((r) =>
        r.methods[method]?.condorcet_consistent === true ? 1
        : r.methods[method]?.condorcet_consistent === false ? 0
        : null
      );

      // Winner stability: fraction of runs where winner = most common winner
      const winners = comparisonResults.map((r) => r.methods[method]?.winner ?? null).filter(Boolean) as string[];
      let stability: number | null = null;
      if (winners.length > 0) {
        const freq: Record<string, number> = {};
        for (const w of winners) freq[w] = (freq[w] ?? 0) + 1;
        const maxFreq = Math.max(...Object.values(freq));
        stability = maxFreq / winners.length;
      }

      scores[method] = {
        equity:       avg(regretsRaw),     // will be inverted at normalisation
        satisfaction: avg(satisfRaw),
        resistance:   avg(vulnRaw),        // will be inverted at normalisation
        condorcet:    avg(condorcetVals),
        stability,
      };
    }
    return scores;
  }, [comparisonResults, allMethodNames]);

  // ── Normalize each axis (min-max, some inverted) ──────────────────────
  const normalized = useMemo(() => {
    const equity   = minMaxNorm(Object.fromEntries(allMethodNames.map((m) => [m, rawScores[m]?.equity ?? null])), true);
    const satisf   = minMaxNorm(Object.fromEntries(allMethodNames.map((m) => [m, rawScores[m]?.satisfaction ?? null])));
    const resist   = minMaxNorm(Object.fromEntries(allMethodNames.map((m) => [m, rawScores[m]?.resistance ?? null])), true);
    const condorcet = minMaxNorm(Object.fromEntries(allMethodNames.map((m) => [m, rawScores[m]?.condorcet ?? null])));
    const stab     = minMaxNorm(Object.fromEntries(allMethodNames.map((m) => [m, rawScores[m]?.stability ?? null])));
    return { equity, satisf, resist, condorcet, stab };
  }, [rawScores, allMethodNames]);

  // ── Global score = mean of 5 normalised dimensions ────────────────────
  const globalScore = useMemo(() => {
    const scores: Record<string, number> = {};
    for (const m of allMethodNames) {
      const dims = [
        normalized.equity[m],
        normalized.satisf[m],
        normalized.resist[m],
        normalized.condorcet[m],
        normalized.stab[m],
      ].filter((v): v is number => v !== undefined);
      scores[m] = dims.length > 0 ? dims.reduce((a, b) => a + b, 0) / dims.length : 0;
    }
    return scores;
  }, [normalized, allMethodNames]);

  // Best method by global score
  const bestMethod = useMemo(() =>
    allMethodNames.reduce((best, m) =>
      (globalScore[m] ?? 0) > (globalScore[best] ?? 0) ? m : best,
      allMethodNames[0] ?? ''
    ),
    [globalScore, allMethodNames]
  );

  // ── Default visible: top 5 by global score (or all if ≤ 5) ───────────
  const [visibleMethods, setVisibleMethods] = useState<Set<string>>(() => {
    const top5 = [...candidateMethods]
      .sort((a, b) => (globalScore[b] ?? 0) - (globalScore[a] ?? 0))
      .slice(0, 5);
    return new Set(top5);
  });

  const toggleMethod = (m: string) =>
    setVisibleMethods((prev) => {
      const next = new Set(prev);
      next.has(m) ? next.delete(m) : next.add(m);
      return next;
    });

  // ── Radar data (one entry per axis) ──────────────────────────────────
  const AXES = [
    { key: 'equity',    label: t('simulation.radar.axisEquity') },
    { key: 'satisf',    label: t('simulation.radar.axisSatisfaction') },
    { key: 'resist',    label: t('simulation.radar.axisStrategic') },
    { key: 'condorcet', label: t('simulation.radar.axisCondorcet') },
    { key: 'stab',      label: t('simulation.radar.axisStability') },
  ] as const;

  const radarData = AXES.map(({ key, label }) => {
    const row: Record<string, string | number> = { axis: label };
    for (const m of candidateMethods) {
      row[m] = normalized[key][m] ?? 0;
    }
    return row;
  });

  // ── Tooltip formatter ─────────────────────────────────────────────────
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    return (
      <div className="rounded p-2" style={{ background: 'var(--bs-body-bg)', border: '1px solid var(--bs-border-color)', fontSize: '0.75rem' }}>
        <strong>{label}</strong>
        {payload.map((p: any) => (
          <div key={p.name} style={{ color: p.color }}>
            {p.name}: {(p.value * 100).toFixed(0)}%
          </div>
        ))}
      </div>
    );
  };

  if (comparisonResults.length === 0) return null;

  const visibleCandidates = candidateMethods.filter((m) => visibleMethods.has(m));

  return (
    <div>
      {/* Best method badge */}
      {bestMethod && (
        <div className="d-flex align-items-center justify-content-center gap-2 mb-3">
          <Badge
            style={{ background: RADAR_COLORS[candidateMethods.indexOf(bestMethod) % RADAR_COLORS.length], fontSize: '0.82rem', padding: '6px 12px' }}
          >
            🏆 {t('simulation.radar.bestMethod')}: {bestMethod}
          </Badge>
          <span className="text-muted small">
            ({t('simulation.radar.bestMethodDesc')})
          </span>
        </div>
      )}

      {/* Radar chart */}
      <ResponsiveContainer width="100%" height={400}>
        <RadarChart data={radarData} margin={{ top: 10, right: 40, bottom: 10, left: 40 }}>
          <PolarGrid stroke="var(--bs-border-color)" />
          <PolarAngleAxis
            dataKey="axis"
            tick={{ fontSize: 12, fill: 'var(--bs-body-color)' }}
          />
          <PolarRadiusAxis
            angle={90}
            domain={[0, 1]}
            tick={{ fontSize: 9 }}
            tickCount={4}
            tickFormatter={(v: number) => `${Math.round(v * 100)}%`}
          />
          <Tooltip content={<CustomTooltip />} />
          {visibleCandidates.map((method, idx) => {
            const colorIdx = candidateMethods.indexOf(method);
            const color    = RADAR_COLORS[colorIdx % RADAR_COLORS.length];
            return (
              <Radar
                key={method}
                name={method}
                dataKey={method}
                stroke={color}
                fill={color}
                fillOpacity={0.18}
                strokeWidth={2}
                dot={{ r: 4, fill: color }}
                isAnimationActive
                animationDuration={600}
              />
            );
          })}
          <Legend
            wrapperStyle={{ paddingTop: 12, fontSize: '0.8rem' }}
            onClick={(e) => toggleMethod(e.dataKey as string)}
            formatter={(value) => (
              <span style={{ opacity: visibleMethods.has(value) ? 1 : 0.4 }}>{value}</span>
            )}
          />
        </RadarChart>
      </ResponsiveContainer>

      {/* Method checkboxes */}
      <div className="mt-2">
        <div className="small text-muted mb-2">{t('simulation.radar.selectMethods')}</div>
        <div className="d-flex flex-wrap gap-2">
          {candidateMethods.map((method, idx) => {
            const color   = RADAR_COLORS[idx % RADAR_COLORS.length];
            const checked = visibleMethods.has(method);
            const score   = globalScore[method] ?? 0;
            return (
              <Check
                key={method}
                type="checkbox"
                id={`radar-cb-${method}`}
                checked={checked}
                onChange={() => toggleMethod(method)}
                label={
                  <span className="d-inline-flex align-items-center gap-1">
                    <span style={{ width: 10, height: 10, borderRadius: 2, background: color, display: 'inline-block', opacity: checked ? 1 : 0.3 }} />
                    <span style={{ opacity: checked ? 1 : 0.5 }}>
                      {method}
                      {method === bestMethod && ' 🏆'}
                    </span>
                    <span className="text-muted" style={{ fontSize: '0.68rem' }}>
                      ({Math.round(score * 100)}%)
                    </span>
                  </span>
                }
                style={{ fontSize: '0.78rem' }}
              />
            );
          })}
        </div>
      </div>

      {/* Axis legend */}
      <div className="d-flex flex-wrap gap-3 mt-3 p-2 rounded" style={{ background: 'var(--bs-secondary-bg, #f8f9fa)', fontSize: '0.72rem' }}>
        {AXES.map(({ label }) => (
          <span key={label} className="text-muted">
            <strong>{label}</strong>: {t(`simulation.radar.axisDesc_${label.toLowerCase().replace(/[^a-z]/g, '_')}`, { defaultValue: '' })}
          </span>
        ))}
      </div>
    </div>
  );
};

export default MethodRadarChart;
