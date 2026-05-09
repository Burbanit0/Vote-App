import React, { useMemo } from 'react';
import { Card } from 'react-bootstrap';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { SimulationCompareResult } from '../../types';
import { METHOD_LABELS } from './simulationConstants';

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
  const metricsData = useMemo(() => {
    if (!comparisonResults.length) return [];
    return allMethodNames.map((method) => {
      const values = comparisonResults.map((r) => r.methods[method]);
      return {
        method: METHOD_LABELS[method] || method,
        'Régret bayésien': round(avg(values.map((v) => v.bayesian_regret ?? 0))),
        'Satisfaction majoritaire': round(avg(values.map((v) => v.majority_satisfaction ?? 0))),
        'Vulnérabilité stratégique': round(avg(values.map((v) => v.strategic_vulnerability ?? 0))),
      };
    });
  }, [comparisonResults, allMethodNames]);

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
          {[
            { label: 'Régret bayésien', color: '#e15759', note: 'plus bas = mieux' },
            { label: 'Satisfaction majoritaire', color: '#59a14f', note: 'plus haut = mieux' },
            { label: 'Vulnérabilité stratégique', color: '#f28e2b', note: 'plus bas = mieux' },
          ].map(({ label, color, note }) => (
            <span key={label} className="d-flex align-items-center gap-1">
              <span style={{ display: 'inline-block', width: 14, height: 14, borderRadius: 2, backgroundColor: color }} />
              <small>{label} <span className="text-muted">({note})</span></small>
            </span>
          ))}
        </div>
        <ResponsiveContainer width="100%" height={380}>
          <BarChart data={metricsData} margin={{ bottom: 90, left: 10, right: 10 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="method" tick={{ fontSize: 11 }} angle={-45} textAnchor="end" interval={0} />
            <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} />
            <Tooltip formatter={(v: number) => v.toFixed(3)} />
            <Bar dataKey="Régret bayésien" fill="#e15759" />
            <Bar dataKey="Satisfaction majoritaire" fill="#59a14f" />
            <Bar dataKey="Vulnérabilité stratégique" fill="#f28e2b" />
          </BarChart>
        </ResponsiveContainer>
      </Card.Body>
    </Card>
  );
};

export default MetricsTab;
