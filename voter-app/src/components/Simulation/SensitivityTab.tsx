import React, { useMemo, useState } from 'react';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { Control, Select } from '@/components/ui/form-controls';
import { Col, Row } from '@/components/ui/grid';
import { Spinner } from '@/components/ui/spinner';
import { Table } from '@/components/ui/table';
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
import { SensitivityResult } from '../../types';
import { getSensitivityAnalysis } from '../../services/simulationCompareApi';
import { CANDIDATE_PALETTE, METHOD_LABELS, METHOD_LINE_COLORS } from './simulationConstants';

const DEFAULT_VALUES: Record<string, string> = {
  ideology_distribution: 'random, centrist, polarized, left_skewed, right_skewed',
  num_voters: '100, 250, 500, 1000, 2000',
  strategic_pct: '0, 10, 20, 30, 40, 50',
};

interface Props {
  baseConfig: { numVoters: number; candidates: string[]; ideology_distribution: string };
}

const SensitivityTab: React.FC<Props> = ({ baseConfig }) => {
  const [variable, setVariable] = useState<'ideology_distribution' | 'num_voters' | 'strategic_pct'>(
    'ideology_distribution'
  );
  const [valuesInput, setValuesInput] = useState(DEFAULT_VALUES.ideology_distribution);
  const [data, setData] = useState<SensitivityResult | null>(null);
  const [loading, setLoading] = useState(false);

  const run = async () => {
    const raw = valuesInput.split(',').map((s) => s.trim()).filter(Boolean);
    if (!raw.length) return;
    const parsedValues: (string | number)[] =
      variable === 'ideology_distribution' ? raw : raw.map(Number).filter((n) => !isNaN(n));
    if (!parsedValues.length) return;

    setLoading(true);
    try {
      const result = await getSensitivityAnalysis({
        base_config: {
          num_voters: baseConfig.numVoters,
          candidates: baseConfig.candidates,
          ideology_distribution: baseConfig.ideology_distribution,
        },
        variable,
        values: parsedValues,
      });
      setData(result);
    } catch { /* error visible via empty state */ } finally {
      setLoading(false);
    }
  };

  const methodNames = useMemo(
    () => (data?.results.length ? Object.keys(data.results[0].winners_by_method) : []),
    [data]
  );

  const colorMap = useMemo(() => {
    if (!data) return {} as Record<string, string>;
    const names = new Set<string>();
    data.results.forEach((r) =>
      Object.values(r.winners_by_method).forEach((w) => { if (w) names.add(w); })
    );
    return Object.fromEntries(
      [...names].map((n, i) => [n, CANDIDATE_PALETTE[i % CANDIDATE_PALETTE.length]])
    );
  }, [data]);

  const lineData = useMemo(
    () =>
      (data?.results ?? []).map((r) => ({
        label: String(r.value),
        ...Object.fromEntries(
          methodNames.map((m) => [METHOD_LABELS[m] || m, r.regret_by_method[m] ?? null])
        ),
      })),
    [data, methodNames]
  );

  return (
    <Card className="mb-4">
      <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
        <strong>Sensitivity Analysis</strong>
        <span className="text-muted ms-2" style={{ fontSize: '0.85rem' }}>
          — vary one parameter and observe how winners change (uses Scenario A config)
        </span>
      </CardHeader>
      <CardBody>
        <Row className="g-3 align-items-end mb-4">
          <Col md={3}>
            <label className="mb-1 inline-block small mb-1">Variable</label>
            <Select
              size="sm"
              value={variable}
              onChange={(e) => {
                const v = e.target.value as typeof variable;
                setVariable(v);
                setValuesInput(DEFAULT_VALUES[v] ?? '');
              }}
            >
              <option value="ideology_distribution">Electorate distribution</option>
              <option value="num_voters">Number of voters</option>
              <option value="strategic_pct">Strategic voter %</option>
            </Select>
          </Col>
          <Col md={6}>
            <label className="mb-1 inline-block small mb-1">
              Values to test{' '}
              <span className="text-muted">
                (comma-separated{variable !== 'ideology_distribution' ? ', numbers' : ''})
              </span>
            </label>
            <Control
              size="sm"
              type="text"
              value={valuesInput}
              onChange={(e) => setValuesInput(e.target.value)}
            />
          </Col>
          <Col md={3}>
            <Button variant="primary" size="sm" className="w-100" onClick={run} disabled={loading}>
              {loading ? <><Spinner size="sm" className="me-2" />Running…</> : 'Run Sensitivity'}
            </Button>
          </Col>
        </Row>

        {data && (
          <>
            <p className="fw-semibold mb-2">Winner heatmap</p>
            <div style={{ overflowX: 'auto' }} className="mb-4">
              <Table className="[&_th]:p-1 [&_td]:p-1 [&_th]:text-left [&_td]:border-t [&_th]:border-b [&_td]:border-border [&_th]:border-border [&_*]:align-middle [&_th]:border [&_td]:border text-center" style={{ minWidth: 400 }}>
                <thead className="table-light">
                  <tr>
                    <th style={{ minWidth: 130, textAlign: 'left' }}>Method</th>
                    {data.results.map((r) => (
                      <th key={String(r.value)} style={{ minWidth: 90 }}>{String(r.value)}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {methodNames.map((method) => {
                    const winners = data.results.map((r) => r.winners_by_method[method] ?? null);
                    const allSame = winners.every((w) => w === winners[0]);
                    return (
                      <tr key={method} style={!allSame ? { backgroundColor: '#fff8e1' } : undefined}>
                        <td className="text-start ps-2">
                          <strong>{METHOD_LABELS[method] || method}</strong>
                        </td>
                        {winners.map((winner, ci) => (
                          <td key={ci}>
                            {winner ? (
                              <Badge style={{ backgroundColor: colorMap[winner] ?? '#999', fontSize: '0.72rem' }}>
                                {winner}
                              </Badge>
                            ) : <span className="text-muted">—</span>}
                          </td>
                        ))}
                      </tr>
                    );
                  })}
                </tbody>
              </Table>
            </div>
            <small className="text-muted d-block mb-4">
              Highlighted rows indicate methods where the winner changes across values.
            </small>

            <p className="fw-semibold mb-2">Bayesian Regret by value</p>
            <ResponsiveContainer width="100%" height={380}>
              <LineChart data={lineData} margin={{ top: 5, right: 20, bottom: 40, left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="label" tick={{ fontSize: 10 }} angle={-30} textAnchor="end" interval={0} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v: number) => (v !== null ? v.toFixed(4) : '—')} />
                <Legend verticalAlign="bottom" wrapperStyle={{ paddingTop: 10, fontSize: 10 }} />
                {methodNames.map((method) => (
                  <Line
                    key={method}
                    type="monotone"
                    dataKey={METHOD_LABELS[method] || method}
                    stroke={METHOD_LINE_COLORS[method] ?? '#999'}
                    strokeWidth={method === 'plurality' ? 2.5 : 1.5}
                    dot={{ r: 3 }}
                    connectNulls
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </>
        )}

        {!data && !loading && (
          <Alert variant="info" className="mb-0">
            Select a variable, adjust the values and click <strong>Run Sensitivity</strong>.
          </Alert>
        )}
      </CardBody>
    </Card>
  );
};

export default SensitivityTab;
