import React, { useState } from 'react';
import ResponsiveTable from '../shared/ResponsiveTable';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { Control } from '@/components/ui/form-controls';
import { Col, Row } from '@/components/ui/grid';
import { Spinner } from '@/components/ui/spinner';
import { Table } from '@/components/ui/table';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { MultiwinnerResult } from '../../types';
import { getMultiwinner } from '../../services/simulationCompareApi';

// ── Constants ──────────────────────────────────────────────────────────────

const METHOD_LABELS: Record<string, string> = {
  dhondt:                  "D'Hondt",
  sainte_lague:            'Sainte-Laguë',
  largest_remainder_hare:  'Largest Rem. (Hare)',
  largest_remainder_droop: 'Largest Rem. (Droop)',
};

const PROPORTIONAL_METHODS = Object.keys(METHOD_LABELS);

const PARTY_PALETTE = [
  '#4e79a7', '#f28e2b', '#e15759', '#76b7b2',
  '#59a14f', '#edc948', '#b07aa1', '#ff9da7',
  '#9c755f', '#bab0ac',
];

// ── Helpers ────────────────────────────────────────────────────────────────

function pct(v: number, total: number) {
  return total > 0 ? `${((v / total) * 100).toFixed(1)}%` : '—';
}

// ── Component ──────────────────────────────────────────────────────────────

interface PartyRow {
  name: string;
  votes: string;
}

const MultiwinnerAnalysis: React.FC = () => {
  // ── Form state ──
  const [parties, setParties] = useState<PartyRow[]>([
    { name: 'Party A', votes: '38' },
    { name: 'Party B', votes: '26' },
    { name: 'Party C', votes: '18' },
    { name: 'Party D', votes: '12' },
    { name: 'Party E', votes: '6' },
  ]);
  const [numSeats, setNumSeats] = useState(20);
  const [result, setResult] = useState<MultiwinnerResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ── Form handlers ──
  const updateParty = (i: number, field: keyof PartyRow, value: string) => {
    setParties((prev) => prev.map((p, idx) => (idx === i ? { ...p, [field]: value } : p)));
  };

  const addParty = () =>
    setParties((prev) => [...prev, { name: `Party ${String.fromCharCode(65 + prev.length)}`, votes: '5' }]);

  const removeParty = (i: number) =>
    setParties((prev) => prev.filter((_, idx) => idx !== i));

  const runAnalysis = async () => {
    const partyVotes: Record<string, number> = {};
    for (const p of parties) {
      const v = parseFloat(p.votes);
      if (p.name.trim() && !isNaN(v) && v > 0) {
        partyVotes[p.name.trim()] = v;
      }
    }
    if (Object.keys(partyVotes).length < 2) {
      setError('Enter at least 2 parties with valid vote counts.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await getMultiwinner({ party_votes: partyVotes, num_seats: numSeats });
      setResult(data);
    } catch {
      setError('Analysis failed. Make sure the backend is running.');
    } finally {
      setLoading(false);
    }
  };

  // ── Derived data ──
  const partyNames = result ? Object.keys(result.party_votes) : [];
  const totalVotes = result ? Object.values(result.party_votes).reduce((a, b) => a + b, 0) : 0;
  const colorMap = Object.fromEntries(
    partyNames.map((p, i) => [p, PARTY_PALETTE[i % PARTY_PALETTE.length]])
  );

  // Stacked bar chart data: one entry per method, seats per party as keys
  const barData = result
    ? PROPORTIONAL_METHODS.map((method) => ({
        method: METHOD_LABELS[method],
        ...(result as any)[method].seats,
      }))
    : [];

  // ── Render ─────────────────────────────────────────────────────────────
  return (
    <div>
      {/* Input form */}
      <Card className="mb-4">
        <CardHeader className="block space-y-0 border-b border-border px-4 py-2 d-flex align-items-center justify-content-between">
          <strong>Party Vote Distribution</strong>
          <Button size="sm" variant="outline-secondary" onClick={addParty}>
            + Add party
          </Button>
        </CardHeader>
        <CardBody>
          <Row className="g-2 mb-3">
            {parties.map((p, i) => (
              <Col key={i} xs={12} sm={6} md={4} lg={3}>
                <div className="flex items-stretch">
                  <Control
                    placeholder="Party name"
                    value={p.name}
                    onChange={(e) => updateParty(i, 'name', e.target.value)}
                  />
                  <Control
                    type="number"
                    min={0}
                    placeholder="Votes %"
                    value={p.votes}
                    style={{ maxWidth: 72 }}
                    onChange={(e) => updateParty(i, 'votes', e.target.value)}
                  />
                  <Button
                    variant="outline-danger"
                    onClick={() => removeParty(i)}
                    disabled={parties.length <= 2}
                  >
                    ×
                  </Button>
                </div>
              </Col>
            ))}
          </Row>
          <Row className="g-3 align-items-end">
            <Col md={3}>
              <label className="mb-1 inline-block small mb-1">Seats to fill</label>
              <Control
                type="number"
                min={2}
                max={200}
                size="sm"
                value={numSeats}
                onChange={(e) => setNumSeats(Number(e.target.value))}
              />
            </Col>
            <Col md={2}>
              <Button variant="primary" size="sm" className="w-100" onClick={runAnalysis} disabled={loading}>
                {loading ? <><Spinner size="sm" className="me-2" />Running…</> : 'Analyse'}
              </Button>
            </Col>
          </Row>
        </CardBody>
      </Card>

      {error && <Alert variant="danger">{error}</Alert>}

      {!result && !loading && (
        <Alert variant="info">
          Enter vote shares for each party and click <strong>Analyse</strong>.
        </Alert>
      )}

      {result && (
        <>
          {/* Best / worst banner */}
          <div className="d-flex gap-3 mb-4 flex-wrap">
            {result.comparison.most_proportional && (
              <Alert variant="success" className="py-2 mb-0 flex-grow-1">
                <strong>Most proportional:</strong>{' '}
                {METHOD_LABELS[result.comparison.most_proportional]}
                {' '}(Gallagher{' '}
                {(result as any)[result.comparison.most_proportional].metrics.gallagher_index?.toFixed(3)})
              </Alert>
            )}
            {result.comparison.least_proportional && (
              <Alert variant="warning" className="py-2 mb-0 flex-grow-1">
                <strong>Least proportional:</strong>{' '}
                {METHOD_LABELS[result.comparison.least_proportional]}
                {' '}(Gallagher{' '}
                {(result as any)[result.comparison.least_proportional].metrics.gallagher_index?.toFixed(3)})
              </Alert>
            )}
          </div>

          {/* Stacked bar chart */}
          <Card className="mb-4">
            <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
              <strong>Seat Allocation by Method</strong>
              <span className="text-muted ms-2" style={{ fontSize: '0.85rem' }}>
                — each segment = seats for that party; dashed lines = proportional ideal
              </span>
            </CardHeader>
            <CardBody>
              {/* Party colour legend */}
              <div className="d-flex gap-3 mb-3 flex-wrap">
                {partyNames.map((p) => (
                  <span key={p} className="d-flex align-items-center gap-1">
                    <span
                      style={{
                        display: 'inline-block',
                        width: 12,
                        height: 12,
                        borderRadius: 2,
                        backgroundColor: colorMap[p],
                      }}
                    />
                    <small>
                      {p}{' '}
                      <span className="text-muted">
                        ({pct(result.party_votes[p] ?? 0, totalVotes)} of votes)
                      </span>
                    </small>
                  </span>
                ))}
              </div>

              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={barData} margin={{ top: 10, right: 20, bottom: 10, left: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="method" tick={{ fontSize: 11 }} />
                  <YAxis
                    label={{ value: 'Seats', angle: -90, position: 'insideLeft', fontSize: 11 }}
                    tick={{ fontSize: 11 }}
                  />
                  <Tooltip
                    formatter={(value: number, name: string) => [
                      `${value} seats (${pct(value, result.num_seats)})`,
                      name,
                    ]}
                  />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  {/* Proportional ideal reference lines per party */}
                  {partyNames.map((p) => (
                    <ReferenceLine
                      key={`ref-${p}`}
                      y={Math.round((result.party_votes[p] / totalVotes) * result.num_seats)}
                      stroke={colorMap[p]}
                      strokeDasharray="4 2"
                      strokeOpacity={0.5}
                    />
                  ))}
                  {partyNames.map((p) => (
                    <Bar key={p} dataKey={p} stackId="a" fill={colorMap[p]}>
                      {barData.map((_, idx) => (
                        <Cell key={`cell-${idx}`} fill={colorMap[p]} />
                      ))}
                    </Bar>
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </CardBody>
          </Card>

          {/* Metrics table */}
          <Card className="mb-4">
            <CardHeader className="block space-y-0 border-b border-border px-4 py-2"><strong>Proportionality Metrics</strong></CardHeader>
            <CardBody className="p-0">
              <ResponsiveTable>
              <Table className="[&_th]:p-1 [&_td]:p-1 [&_th]:text-left [&_td]:border-t [&_th]:border-b [&_td]:border-border [&_th]:border-border [&_*]:align-middle [&_th]:border [&_td]:border mb-0">
                <thead className="table-light">
                  <tr>
                    <th style={{ minWidth: 170 }}>Method</th>
                    <th className="text-center" title="Gallagher LSq index — 0 = perfectly proportional">
                      Gallagher ↓
                    </th>
                    <th className="text-center" title="Effective number of parties in seats (Laakso-Taagepera)">
                      ENP seats
                    </th>
                    <th className="text-center" title="Most over/under-represented party">
                      Largest deviation
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {result.comparison.gallagher_ranking.map((method, rank) => {
                    const m = (result as any)[method] as { seats: Record<string, number>; metrics: any };
                    const isBest = rank === 0;
                    return (
                      <tr key={method} style={isBest ? { backgroundColor: '#f0fff4' } : undefined}>
                        <td className="fw-semibold ps-2">
                          {METHOD_LABELS[method]}
                          {isBest && (
                            <Badge variant="success" className="ms-2" style={{ fontSize: '0.65rem' }}>
                              best
                            </Badge>
                          )}
                        </td>
                        <td className="text-center">
                          <strong>{m.metrics.gallagher_index?.toFixed(3) ?? '—'}</strong>
                        </td>
                        <td className="text-center">
                          {m.metrics.effective_parties_seats?.toFixed(2) ?? '—'}
                          {' '}
                          <span className="text-muted small">
                            (votes: {m.metrics.effective_parties_votes?.toFixed(2) ?? '—'})
                          </span>
                        </td>
                        <td className="text-center">
                          {m.metrics.largest_deviation ? (
                            <span
                              style={{
                                color:
                                  m.metrics.largest_deviation.deviation > 0 ? '#0d6efd' : '#dc3545',
                              }}
                            >
                              {m.metrics.largest_deviation.party}{' '}
                              {m.metrics.largest_deviation.deviation > 0 ? '+' : ''}
                              {(m.metrics.largest_deviation.deviation * 100).toFixed(1)}%
                            </span>
                          ) : (
                            '—'
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </Table>
              </ResponsiveTable>
            </CardBody>
          </Card>

          {/* Detailed seat breakdown */}
          <Card>
            <CardHeader className="block space-y-0 border-b border-border px-4 py-2"><strong>Seat Breakdown Detail</strong></CardHeader>
            <CardBody className="p-0">
              <ResponsiveTable>
              <Table className="[&_th]:p-1 [&_td]:p-1 [&_th]:text-left [&_td]:border-t [&_th]:border-b [&_td]:border-border [&_th]:border-border [&_*]:align-middle [&_th]:border [&_td]:border mb-0 text-center">
                <thead className="table-light">
                  <tr>
                    <th className="text-start ps-2">Party</th>
                    <th>Votes</th>
                    <th>Ideal</th>
                    {PROPORTIONAL_METHODS.map((m) => (
                      <th key={m}>{METHOD_LABELS[m]}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {partyNames.map((p) => {
                    const votePct = result.party_votes[p] / totalVotes;
                    const idealSeats = (votePct * result.num_seats).toFixed(1);
                    return (
                      <tr key={p}>
                        <td className="text-start ps-2 fw-semibold">
                          <span
                            style={{
                              display: 'inline-block',
                              width: 10,
                              height: 10,
                              borderRadius: 2,
                              backgroundColor: colorMap[p],
                              marginRight: 6,
                            }}
                          />
                          {p}
                        </td>
                        <td className="text-muted">{pct(result.party_votes[p], totalVotes)}</td>
                        <td className="text-muted">{idealSeats}</td>
                        {PROPORTIONAL_METHODS.map((method) => {
                          const seats = (result as any)[method].seats[p] ?? 0;
                          const diff = seats - parseFloat(idealSeats);
                          return (
                            <td
                              key={method}
                              style={{
                                color: Math.abs(diff) > 1 ? (diff > 0 ? '#0d6efd' : '#dc3545') : undefined,
                                fontWeight: Math.abs(diff) > 1 ? 600 : undefined,
                              }}
                            >
                              {seats}
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                  {/* Total row */}
                  <tr className="table-light fw-semibold">
                    <td className="text-start ps-2">Total</td>
                    <td>100%</td>
                    <td>{result.num_seats}</td>
                    {PROPORTIONAL_METHODS.map((method) => (
                      <td key={method}>
                        {Object.values((result as any)[method].seats as Record<string, number>)
                          .reduce((a, b) => a + b, 0)}
                      </td>
                    ))}
                  </tr>
                </tbody>
              </Table>
              </ResponsiveTable>
            </CardBody>
          </Card>
        </>
      )}
    </div>
  );
};

export default MultiwinnerAnalysis;
