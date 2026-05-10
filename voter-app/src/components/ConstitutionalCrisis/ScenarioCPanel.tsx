import React, { useState } from 'react';
import { Badge, Button, Card, Col, Form, Row, Spinner, Table } from 'react-bootstrap';
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { ConstitutionalResult } from '../../services/simulationCompareApi';

const COLORS = ['#4e79a7', '#e15759', '#59a14f', '#f28e2b', '#76b7b2', '#edc948'];

const METHOD_LABELS_MULTI: Record<string, string> = {
  dhondt: "D'Hondt",
  sainte_lague: 'Sainte-Laguë',
  largest_remainder_hare: 'LR-Hare',
};

interface Props {
  result: ConstitutionalResult | null;
  loading: boolean;
  onRun: (numSeats: number) => void;
}

const ScenarioCPanel: React.FC<Props> = ({ result, loading, onRun }) => {
  const [numSeats, setNumSeats] = useState(100);

  const multi = result?.multiwinner as Record<string, any> | undefined;
  const partyVotes = result?.party_votes ?? {};
  const parties = Object.keys(partyVotes);
  const colorMap = Object.fromEntries(parties.map((p, i) => [p, COLORS[i % COLORS.length]]));
  const totalVotes = Object.values(partyVotes).reduce((a, b) => a + b, 0);

  // Stacked bar chart data: one entry per proportional method
  const chartData = Object.entries(METHOD_LABELS_MULTI).map(([key, label]) => {
    const seats = multi?.[key]?.seats ?? {};
    const gallagher = multi?.[key]?.metrics?.gallagher_index;
    return {
      method: label,
      gallagher,
      ...seats,
    };
  });

  return (
    <div>
      <p className="text-muted small mb-3">
        Face à la crise, le parlement est dissous et remplacé par une assemblée constituante proportionnelle.
        Comparez comment les différentes méthodes de scrutin proportionnel répartissent les sièges.
      </p>

      <Row className="g-3 mb-4">
        <Col md={5}>
          <Card>
            <Card.Body>
              <Form.Label>
                Nombre de sièges à l'assemblée : <strong>{numSeats}</strong>
              </Form.Label>
              <Form.Range min={10} max={500} step={10} value={numSeats} onChange={(e) => setNumSeats(Number(e.target.value))} />
              <div className="d-flex justify-content-between">
                <small className="text-muted">10</small><small className="text-muted">500</small>
              </div>
            </Card.Body>
          </Card>
        </Col>
        <Col md={7}>
          <Card>
            <Card.Body>
              <small className="fw-semibold text-muted d-block mb-2">Distribution des votes au 1er tour</small>
              <div className="d-flex flex-wrap gap-2">
                {parties.map((p) => (
                  <span key={p} className="d-flex align-items-center gap-1">
                    <span style={{ width: 12, height: 12, borderRadius: 2, backgroundColor: colorMap[p], display: 'inline-block' }} />
                    <small>{p} — {Math.round(partyVotes[p] / totalVotes * 100)}%</small>
                  </span>
                ))}
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      <div className="mb-4">
        <Button variant="success" onClick={() => onRun(numSeats)} disabled={loading}>
          {loading ? <><Spinner size="sm" className="me-2" />Simulation…</> : '▶ Composer l\'assemblée'}
        </Button>
      </div>

      {multi && (
        <>
          {/* Stacked bar chart */}
          <Card className="mb-4">
            <Card.Header><strong>Répartition des sièges par méthode proportionnelle</strong></Card.Header>
            <Card.Body>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={chartData} layout="vertical" margin={{ left: 80, right: 30 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" domain={[0, numSeats]} tick={{ fontSize: 11 }} />
                  <YAxis type="category" dataKey="method" tick={{ fontSize: 11 }} width={80} />
                  <Tooltip formatter={(v: number) => `${v} siège(s)`} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  {parties.map((p) => (
                    <Bar key={p} dataKey={p} stackId="a" fill={colorMap[p]} />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </Card.Body>
          </Card>

          {/* Detail table */}
          <Table bordered size="sm" className="mb-3">
            <thead className="table-light">
              <tr>
                <th>Méthode</th>
                {parties.map((p) => (
                  <th key={p} className="text-center">
                    <span style={{ display: 'inline-block', width: 10, height: 10, backgroundColor: colorMap[p], borderRadius: 2, marginRight: 4 }} />
                    {p}
                  </th>
                ))}
                <th className="text-center">Gallagher</th>
                <th className="text-center">Plus proportionnel ?</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(METHOD_LABELS_MULTI).map(([key, label]) => {
                const seats = multi[key]?.seats ?? {};
                const gallagher = multi[key]?.metrics?.gallagher_index;
                const isBest = multi.comparison?.most_proportional === key;
                return (
                  <tr key={key} style={isBest ? { backgroundColor: '#e8f4e8' } : undefined}>
                    <td className="fw-semibold ps-2">{label}</td>
                    {parties.map((p) => (
                      <td key={p} className="text-center">{seats[p] ?? 0}</td>
                    ))}
                    <td className="text-center">
                      {gallagher != null ? <Badge bg={gallagher < 0.05 ? 'success' : gallagher < 0.1 ? 'warning' : 'danger'} text={gallagher < 0.1 ? 'dark' : undefined}>{gallagher.toFixed(3)}</Badge> : '—'}
                    </td>
                    <td className="text-center">{isBest ? <span style={{ color: '#198754' }}>✓</span> : ''}</td>
                  </tr>
                );
              })}
              {/* Uninominal comparison */}
              {result?.uninominal_winner && (
                <tr style={{ backgroundColor: '#fff8e1' }}>
                  <td className="fw-semibold ps-2 text-warning-emphasis">Scrutin uninominal</td>
                  {parties.map((p) => (
                    <td key={p} className="text-center text-muted">
                      {p === result.uninominal_winner ? numSeats : 0}
                    </td>
                  ))}
                  <td className="text-center">
                    <Badge bg="danger">Très élevé</Badge>
                  </td>
                  <td className="text-center"><span className="text-danger">✗ Spoiler effect</span></td>
                </tr>
              )}
            </tbody>
          </Table>
          <small className="text-muted d-block mb-3">
            Gallagher ≈ 0 = proportionnel parfait · {'>'}0.10 = fort biais · Scrutin uninominal = 100% des sièges au vainqueur (simulation)
          </small>

          <Card className="border-0" style={{ backgroundColor: '#f8f9fa' }}>
            <Card.Body>
              <small className="fw-semibold">📋 Analyse :</small>
              <p className="mb-0 mt-1 text-muted" style={{ fontSize: '0.85rem' }}>{result?.conclusion}</p>
            </Card.Body>
          </Card>
        </>
      )}
    </div>
  );
};

export default ScenarioCPanel;
