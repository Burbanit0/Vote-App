import React, { useMemo } from 'react';
import { Card } from 'react-bootstrap';
import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { SimulationCompareResult } from '../../types';
import { METHOD_LABELS } from './simulationConstants';
import { useChartTheme } from '../../hooks/useChartTheme';
import EmptyChart from '../shared/EmptyChart';

function avg(values: number[]): number {
  return values.length === 0 ? 0 : values.reduce((a, b) => a + b, 0) / values.length;
}

function round(value: number, decimals = 3): number {
  return Math.round(value * 10 ** decimals) / 10 ** decimals;
}

interface Props {
  comparisonResults: SimulationCompareResult[];
  allMethodNames: string[];
  numSimulations: number;
}

const MetricsTab: React.FC<Props> = ({ comparisonResults, allMethodNames, numSimulations }) => {
  const ct = useChartTheme();

  const metricsData = useMemo(() => {
    if (!comparisonResults.length) return [];
    return allMethodNames.map((method) => {
      const values = comparisonResults.map((r) => r.methods[method]);
      return {
        method: METHOD_LABELS[method] || method,
        'Régret bayésien':        round(avg(values.map((v) => v.bayesian_regret ?? 0))),
        'Satisfaction majoritaire': round(avg(values.map((v) => v.majority_satisfaction ?? 0))),
        'Vulnérabilité stratégique': round(avg(values.map((v) => v.strategic_vulnerability ?? 0))),
      };
    });
  }, [comparisonResults, allMethodNames]);

  // Median of Bayesian Regret — used as a reference line
  const medianRegret = useMemo(() => {
    if (!metricsData.length) return null;
    const sorted = [...metricsData]
      .map((d) => d['Régret bayésien'])
      .sort((a, b) => a - b);
    return sorted[Math.floor(sorted.length / 2)];
  }, [metricsData]);

  const METRICS = [
    { key: 'Régret bayésien',         color: '#e15759', note: 'plus bas = mieux' },
    { key: 'Satisfaction majoritaire', color: '#59a14f', note: 'plus haut = mieux' },
    { key: 'Vulnérabilité stratégique', color: '#f28e2b', note: 'plus bas = mieux' },
  ];

  return (
    <Card className="mb-4">
      <Card.Header>
        <strong>Métriques comparatives</strong>
        <span className="text-muted ms-2" style={{ fontSize: '0.85rem' }}>
          — moyenne sur {numSimulations} simulations (Scénario A)
        </span>
      </Card.Header>
      <Card.Body>
        <div className="d-flex gap-4 mb-3 flex-wrap">
          {METRICS.map(({ key, color, note }) => (
            <span key={key} className="d-flex align-items-center gap-1">
              <span style={{ display: 'inline-block', width: 14, height: 14, borderRadius: 2, backgroundColor: color }} />
              <small>{key} <span className="text-muted">({note})</span></small>
            </span>
          ))}
        </div>

        {metricsData.length === 0 ? (
          <EmptyChart height={380} />
        ) : (
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={metricsData} margin={{ top: 20, bottom: 90, left: 10, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} />
              <XAxis
                dataKey="method"
                tick={{ fontSize: 11, fill: ct.tickFill }}
                angle={-45}
                textAnchor="end"
                interval={0}
              />
              <YAxis domain={[0, 1]} tick={{ fontSize: 11, fill: ct.tickFill }} />
              <Tooltip formatter={(v: number) => v.toFixed(3)} contentStyle={ct.tooltipStyle} />

              {/* Median reference line for Bayesian Regret */}
              {medianRegret !== null && (
                <ReferenceLine
                  y={medianRegret}
                  stroke="#6c757d"
                  strokeDasharray="5 3"
                  label={{
                    value: `médiane: ${medianRegret.toFixed(3)}`,
                    fontSize: 9,
                    fill: '#6c757d',
                    position: 'insideTopRight',
                  }}
                />
              )}

              {METRICS.map(({ key, color }) => (
                <Bar key={key} dataKey={key} fill={color} maxBarSize={28}>
                  <LabelList
                    dataKey={key}
                    position="top"
                    style={{ fontSize: 8, fill: ct.tickFill }}
                    formatter={(v: unknown) => typeof v === 'number' ? v.toFixed(2) : ''}
                  />
                </Bar>
              ))}
            </BarChart>
          </ResponsiveContainer>
        )}
      </Card.Body>
    </Card>
  );
};

export default MetricsTab;
