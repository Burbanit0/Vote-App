import React, { useMemo } from 'react';
import { Alert, Card } from 'react-bootstrap';
import { useChartTheme } from '../../hooks/useChartTheme';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { StrategicImpactPoint } from '../../types';
import { METHOD_LABELS, METHOD_LINE_COLORS } from './simulationConstants';

interface Props {
  strategicData: StrategicImpactPoint[];
  allMethodNames: string[];
}

const StrategicImpactTab: React.FC<Props> = ({ strategicData, allMethodNames }) => {
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

  return (
    <Card className="mb-4">
      <Card.Header>
        <strong>Strategic Voting Impact on Bayesian Regret</strong>
        <span className="text-muted ms-2" style={{ fontSize: '0.85rem' }}>
          — how each method degrades as the proportion of strategic voters increases
        </span>
      </Card.Header>
      <Card.Body>
        <p className="text-muted small mb-3">
          Methods whose line rises steeply are more vulnerable to tactical voting.
          Flat lines indicate resistance to strategic manipulation.
        </p>
        {strategicData.length > 0 ? (
          <ResponsiveContainer width="100%" height={420}>
            <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 20, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} />
              <XAxis
                dataKey="pct"
                tick={{ fill: ct.tickFill }}
                label={{ value: 'Strategic voters (%)', position: 'insideBottom', offset: -10, fontSize: 12, fill: ct.tickFill }}
              />
              <YAxis
                tick={{ fontSize: 11, fill: ct.tickFill }}
                label={{ value: 'Bayesian Regret', angle: -90, position: 'insideLeft', fontSize: 12, fill: ct.tickFill }}
              />
              <Tooltip formatter={(v: number) => (v !== null ? v.toFixed(4) : '—')} contentStyle={ct.tooltipStyle} />
              <Legend verticalAlign="bottom" wrapperStyle={{ paddingTop: 20, fontSize: 11 }} />
              {allMethodNames.map((method) => (
                <Line
                  key={method}
                  type="monotone"
                  dataKey={METHOD_LABELS[method] || method}
                  stroke={METHOD_LINE_COLORS[method] ?? '#999'}
                  strokeWidth={method === 'plurality' ? 2.5 : 1.5}
                  dot={false}
                  activeDot={{ r: 4 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <Alert variant="info">No strategic impact data available.</Alert>
        )}
      </Card.Body>
    </Card>
  );
};

export default StrategicImpactTab;
