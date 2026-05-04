import React, { useState } from 'react';
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  Form,
  Row,
  Spinner,
  Table,
} from 'react-bootstrap';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { BandwagonResult } from '../../types';
import { getBandwagonAnalysis, BandwagonParams } from '../../services/simulationCompareApi';

// ── Constants ──────────────────────────────────────────────────────────────

const METHOD_LABELS: Record<string, string> = {
  plurality:        'Plurality',
  two_round:        'Two-Round',
  borda:            'Borda',
  approval:         'Approval',
  irv:              'IRV',
  coombs:           "Coombs'",
  bucklin:          'Bucklin',
  minimax:          'Minimax',
  schulze:          'Schulze',
  condorcet:        'Condorcet',
  positional_score: 'Positional Score',
};

const CANDIDATE_COLORS = [
  '#4e79a7', '#f28e2b', '#e15759', '#76b7b2',
  '#59a14f', '#edc948', '#b07aa1', '#ff9da7',
];

const METHOD_COLORS = [
  '#e15759', '#4e79a7', '#59a14f', '#f28e2b',
  '#76b7b2', '#edc948', '#b07aa1', '#9c755f',
  '#bab0ac', '#86bcb6', '#499894',
];

// ── Helpers ────────────────────────────────────────────────────────────────

function amplificationLabel(rate: number): { label: string; variant: string } {
  if (rate <= 0.1) return { label: 'Résiste',              variant: 'success' };
  if (rate <= 0.3) return { label: 'Amplifie légèrement',  variant: 'warning' };
  return              { label: 'Amplifie fortement',        variant: 'danger'  };
}

// ── Component ──────────────────────────────────────────────────────────────

interface Props {
  baseParams: CompareBaseParams;
}

interface CompareBaseParams {
  num_voters?: number;
  candidates?: string[];
  ideology_distribution?: string;
}

const BandwagonAnalysis: React.FC<Props> = ({ baseParams }) => {
  const [numRounds, setNumRounds] = useState(6);
  const [influenceStrength, setInfluenceStrength] = useState(0.3);
  const [result, setResult] = useState<BandwagonResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runSimulation = async () => {
    setLoading(true);
    setError(null);
    try {
      const params: BandwagonParams = {
        ...baseParams,
        num_rounds: numRounds,
        influence_strength: influenceStrength,
      };
      const data = await getBandwagonAnalysis(params);
      setResult(data);
    } catch {
      setError('Simulation failed. Make sure the backend is running.');
    } finally {
      setLoading(false);
    }
  };

  // ── Derived chart data ──────────────────────────────────────────────────

  const candidateNames = result
    ? Object.keys(result.rounds[0]?.poll_standings ?? {})
    : [];

  const methodNames = result
    ? Object.keys(result.rounds[0]?.methods ?? {})
    : [];

  const pollChartData = result?.rounds.map((r) => ({
    round: `R${r.round}`,
    ...r.poll_standings,
    polarization: r.voter_lean_distribution.polarization_index,
  })) ?? [];

  const regretChartData = result?.rounds.map((r) => ({
    round: `R${r.round}`,
    ...Object.fromEntries(
      Object.entries(r.methods).map(([m, d]) => [METHOD_LABELS[m] ?? m, d.bayesian_regret])
    ),
  })) ?? [];

  // ── Render ─────────────────────────────────────────────────────────────

  return (
    <div>
      {/* Controls */}
      <Card className="mb-4">
        <Card.Header><strong>Bandwagon Simulation Controls</strong></Card.Header>
        <Card.Body>
          <Row className="g-3 align-items-end">
            <Col md={3}>
              <Form.Label className="small mb-1">
                Rounds: <strong>{numRounds}</strong>
              </Form.Label>
              <Form.Range
                min={2} max={12} value={numRounds}
                onChange={(e) => setNumRounds(Number(e.target.value))}
              />
            </Col>
            <Col md={4}>
              <Form.Label className="small mb-1">
                Influence strength:{' '}
                <strong>{influenceStrength.toFixed(2)}</strong>
                <span className="text-muted ms-1">
                  ({influenceStrength < 0.2 ? 'weak' : influenceStrength < 0.5 ? 'moderate' : 'strong'})
                </span>
              </Form.Label>
              <Form.Range
                min={0} max={1} step={0.05} value={influenceStrength}
                onChange={(e) => setInfluenceStrength(Number(e.target.value))}
              />
            </Col>
            <Col md={2}>
              <Button
                variant="primary"
                className="w-100"
                onClick={runSimulation}
                disabled={loading}
              >
                {loading ? (
                  <><Spinner size="sm" className="me-2" />Running…</>
                ) : (
                  'Run'
                )}
              </Button>
            </Col>
          </Row>
          <p className="text-muted small mt-2 mb-0">
            Simulates how poll standings feed back into voter preferences round by round.
            Uses Scenario A configuration. Higher influence strength = stronger bandwagon.
          </p>
        </Card.Body>
      </Card>

      {error && <Alert variant="danger">{error}</Alert>}

      {!result && !loading && (
        <Alert variant="info">
          Adjust the parameters and click <strong>Run</strong> to simulate the bandwagon effect.
        </Alert>
      )}

      {result && (
        <>
          {/* Convergence info */}
          {result.convergence_round !== null ? (
            <Alert variant="success" className="py-2 mb-4">
              Plurality winner stabilised at <strong>round {result.convergence_round}</strong>.
            </Alert>
          ) : (
            <Alert variant="warning" className="py-2 mb-4">
              Plurality winner did not converge within {result.num_rounds} rounds.
            </Alert>
          )}

          {/* Chart 1: Poll standings evolution */}
          <Card className="mb-4">
            <Card.Header>
              <strong>Poll Standings Evolution</strong>
              <span className="text-muted ms-2" style={{ fontSize: '0.85rem' }}>
                — how first-choice support shifts across rounds
              </span>
            </Card.Header>
            <Card.Body>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={pollChartData} margin={{ top: 5, right: 20, bottom: 10, left: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="round" tick={{ fontSize: 11 }} />
                  <YAxis
                    tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
                    domain={[0, 1]}
                    tick={{ fontSize: 11 }}
                  />
                  <Tooltip formatter={(v: number) => `${(v * 100).toFixed(1)}%`} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <ReferenceLine y={0.5} stroke="#ccc" strokeDasharray="4 2" />
                  {candidateNames.map((name, i) => (
                    <Line
                      key={name}
                      type="monotone"
                      dataKey={name}
                      stroke={CANDIDATE_COLORS[i % CANDIDATE_COLORS.length]}
                      strokeWidth={2}
                      dot={{ r: 4 }}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </Card.Body>
          </Card>

          {/* Chart 2: Bayesian regret per method */}
          <Card className="mb-4">
            <Card.Header>
              <strong>Bayesian Regret Across Rounds</strong>
              <span className="text-muted ms-2" style={{ fontSize: '0.85rem' }}>
                — flat lines resist bandwagon; rising lines amplify it
              </span>
            </Card.Header>
            <Card.Body>
              <ResponsiveContainer width="100%" height={320}>
                <LineChart data={regretChartData} margin={{ top: 5, right: 20, bottom: 20, left: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="round" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(v: number) => (v != null ? v.toFixed(4) : '—')} />
                  <Legend
                    verticalAlign="bottom"
                    wrapperStyle={{ paddingTop: 10, fontSize: 10 }}
                  />
                  {methodNames.map((method, i) => (
                    <Line
                      key={method}
                      type="monotone"
                      dataKey={METHOD_LABELS[method] ?? method}
                      stroke={METHOD_COLORS[i % METHOD_COLORS.length]}
                      strokeWidth={method === 'plurality' ? 2.5 : 1.5}
                      dot={false}
                      activeDot={{ r: 4 }}
                      connectNulls
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </Card.Body>
          </Card>

          {/* Table: amplification summary */}
          <Card>
            <Card.Header>
              <strong>Resistance Summary</strong>
              <span className="text-muted ms-2" style={{ fontSize: '0.85rem' }}>
                — proportion of rounds where the winner differs from round 0
              </span>
            </Card.Header>
            <Card.Body className="p-0">
              <Table bordered size="sm" className="mb-0">
                <thead className="table-light">
                  <tr>
                    <th style={{ minWidth: 150 }}>Method</th>
                    <th className="text-center" style={{ minWidth: 120 }}>
                      Amplification
                    </th>
                    <th className="text-center">Verdict</th>
                    <th className="text-center" style={{ minWidth: 100 }}>
                      R0 winner
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(result.amplification_by_method)
                    .sort((a, b) => a[1] - b[1])
                    .map(([method, rate]) => {
                      const { label, variant } = amplificationLabel(rate);
                      const r0winner = result.rounds[0]?.methods[method]?.winner;
                      return (
                        <tr key={method}>
                          <td className="fw-semibold ps-2">
                            {METHOD_LABELS[method] ?? method}
                          </td>
                          <td className="text-center">
                            <div
                              style={{
                                height: 6,
                                backgroundColor: '#e9ecef',
                                borderRadius: 3,
                                overflow: 'hidden',
                              }}
                            >
                              <div
                                style={{
                                  height: '100%',
                                  width: `${rate * 100}%`,
                                  backgroundColor:
                                    variant === 'success' ? '#198754'
                                    : variant === 'warning' ? '#ffc107'
                                    : '#dc3545',
                                  borderRadius: 3,
                                }}
                              />
                            </div>
                            <small className="text-muted">{(rate * 100).toFixed(0)}%</small>
                          </td>
                          <td className="text-center">
                            <Badge bg={variant} style={{ fontSize: '0.75rem' }}>
                              {label}
                            </Badge>
                          </td>
                          <td className="text-center text-muted small">
                            {r0winner ?? '—'}
                          </td>
                        </tr>
                      );
                    })}
                </tbody>
              </Table>
            </Card.Body>
          </Card>
        </>
      )}
    </div>
  );
};

export default BandwagonAnalysis;
