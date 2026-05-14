import React, { useMemo } from 'react';
import { Card } from 'react-bootstrap';
import { useChartTheme } from '../../hooks/useChartTheme';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { StrategicImpactPoint } from '../../types';
import { METHOD_LABELS, METHOD_LINE_COLORS } from './simulationConstants';
import EmptyChart from '../shared/EmptyChart';
import { useTranslation } from 'react-i18next';

interface Props {
  strategicData: StrategicImpactPoint[];
  allMethodNames: string[];
}

const StrategicImpactTab: React.FC<Props> = ({ strategicData, allMethodNames }) => {
  const { t } = useTranslation();
  const ct = useChartTheme();

  const chartData = useMemo(
    () =>
      strategicData.map((point) => ({
        pct: `${point.strategic_pct}%`,
        ...Object.fromEntries(
          Object.entries(point.methods).map(([m, v]) => [METHOD_LABELS[m] || m, v])
        ),
      })),
    [strategicData]
  );

  // Maximum observed regret — used for the "vulnérables" annotation placement
  const maxRegret = useMemo(() => {
    if (!strategicData.length) return 0.5;
    const vals = strategicData.flatMap((p) =>
      Object.values(p.methods).map((v) => v ?? 0)
    );
    return Math.max(...vals, 0.1);
  }, [strategicData]);

  return (
    <Card className="mb-4">
      <Card.Header>
        <strong>{t('simulation.strategicImpactTitle')}</strong>
        <span className="text-muted ms-2" style={{ fontSize: '0.85rem' }}>
          {t('simulation.strategicImpactSubtitle')}
        </span>
      </Card.Header>
      <Card.Body>
        <p className="text-muted small mb-3">
          {t('simulation.strategicRise')}
          {' '}
          {t('simulation.strategicFlat')}
          {' '}
          <strong style={{ color: '#dc3545' }}>{t('methods.plurality.label')}</strong>
          {' '}
          {t('simulation.strategicHighlighted')}
        </p>

        {strategicData.length === 0 ? (
          <EmptyChart height={420} />
        ) : (
          <ResponsiveContainer width="100%" height={440}>
            <LineChart data={chartData} margin={{ top: 10, right: 20, bottom: 30, left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} />

              {/* Green zone: acceptable regret (≤ 0.05) */}
              <ReferenceArea
                y1={0}
                y2={0.05}
                fill="#d4edda"
                fillOpacity={ct.isDark ? 0.12 : 0.45}
              />
              <ReferenceLine
                y={0.05}
                stroke="#198754"
                strokeDasharray="4 2"
                strokeOpacity={0.7}
                label={{
                  value: t('simulation.acceptableThreshold'),
                  fontSize: 9,
                  fill: '#198754',
                  position: 'insideBottomRight',
                }}
              />

              {/* Y annotations — résistantes (bottom) / vulnérables (top) */}
              <ReferenceLine
                y={maxRegret * 0.92}
                stroke="transparent"
                label={{
                  value: t('simulation.vulnerableMethods'),
                  fontSize: 9,
                  fill: '#dc3545',
                  position: 'insideTopLeft',
                }}
              />
              <ReferenceLine
                y={0.01}
                stroke="transparent"
                label={{
                  value: t('simulation.resistantMethods'),
                  fontSize: 9,
                  fill: '#198754',
                  position: 'insideBottomLeft',
                }}
              />

              <XAxis
                dataKey="pct"
                tick={{ fill: ct.tickFill }}
                label={{ value: t('simulation.strategicVotersAxis'), position: 'insideBottom', offset: -15, fontSize: 12, fill: ct.tickFill }}
              />
              <YAxis
                tick={{ fontSize: 11, fill: ct.tickFill }}
                label={{ value: t('simulation.bayesianRegret'), angle: -90, position: 'insideLeft', fontSize: 12, fill: ct.tickFill }}
              />
              <Tooltip formatter={(v: number) => (v !== null ? v.toFixed(4) : '—')} contentStyle={ct.tooltipStyle} />
              <Legend verticalAlign="bottom" wrapperStyle={{ paddingTop: 24, fontSize: 11 }} />

              {allMethodNames.map((method) => {
                const isPlurality = method === 'plurality';
                return (
                  <Line
                    key={method}
                    type="monotone"
                    dataKey={METHOD_LABELS[method] || method}
                    stroke={isPlurality ? '#dc3545' : METHOD_LINE_COLORS[method] ?? '#999'}
                    strokeWidth={isPlurality ? 3 : 1.5}
                    strokeDasharray={isPlurality ? undefined : undefined}
                    dot={false}
                    activeDot={{ r: isPlurality ? 5 : 3 }}
                    zIndex={isPlurality ? 10 : 1}
                  />
                );
              })}
            </LineChart>
          </ResponsiveContainer>
        )}
      </Card.Body>
    </Card>
  );
};

export default StrategicImpactTab;
