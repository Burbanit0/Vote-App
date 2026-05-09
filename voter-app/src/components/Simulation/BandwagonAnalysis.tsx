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
import SkeletonCard from '../shared/SkeletonCard';

// ── Constants ──────────────────────────────────────────────────────────────

const METHOD_LABELS: Record<string, string> = {
  plurality:        'Pluralité',
  two_round:        'Deux tours',
  borda:            'Borda',
  approval:         'Approbation',
  irv:              'IRV',
  coombs:           "Coombs'",
  bucklin:          'Bucklin',
  minimax:          'Minimax',
  schulze:          'Schulze',
  condorcet:        'Condorcet',
  positional_score: 'Score positionnel',
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
      setError('Simulation échouée. Vérifiez que le backend est démarré.');
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
        <Card.Header><strong>Paramètres de la simulation bandwagon</strong></Card.Header>
        <Card.Body>
          <Row className="g-3 align-items-end">
            <Col md={3}>
              <Form.Label className="small mb-1">
                Tours : <strong>{numRounds}</strong>
              </Form.Label>
              <Form.Range
                min={2} max={12} value={numRounds}
                onChange={(e) => setNumRounds(Number(e.target.value))}
              />
            </Col>
            <Col md={4}>
              <Form.Label className="small mb-1">
                Force d'influence :{' '}
                <strong>{influenceStrength.toFixed(2)}</strong>
                <span className="text-muted ms-1">
                  ({influenceStrength < 0.2 ? 'faible' : influenceStrength < 0.5 ? 'modérée' : 'forte'})
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
                  <><Spinner size="sm" className="me-2" />Simulation…</>
                ) : (
                  'Lancer'
                )}
              </Button>
            </Col>
          </Row>
          <p className="text-muted small mt-2 mb-0">
            Simule comment les sondages influencent les préférences des électeurs tour par tour.
            Utilise la configuration du Scénario A. Force d'influence plus élevée = effet bandwagon plus fort.
          </p>
        </Card.Body>
      </Card>

      {error && <Alert variant="danger">{error}</Alert>}

      {loading && (
        <Row className="g-3 mb-2">
          {[240, 300, 180].map((h, i) => <Col key={i} md={4}><SkeletonCard height={h} /></Col>)}
        </Row>
      )}

      {!result && !loading && (
        <Alert variant="info">
          Ajustez les paramètres et cliquez sur <strong>Lancer</strong> pour simuler l'effet bandwagon.
        </Alert>
      )}

      {result && (
        <>
          {/* Convergence info */}
          {result.convergence_round !== null ? (
            <Alert variant="success" className="py-2 mb-4">
              Le vainqueur en pluralité s'est stabilisé au <strong>tour {result.convergence_round}</strong>.
            </Alert>
          ) : (
            <Alert variant="warning" className="py-2 mb-4">
              Pas de convergence du vainqueur en pluralité sur {result.num_rounds} tours.
            </Alert>
          )}

          {/* Chart 1: Poll standings evolution */}
          <Card className="mb-4">
            <Card.Header>
              <strong>Évolution des sondages</strong>
              <span className="text-muted ms-2" style={{ fontSize: '0.85rem' }}>
                — comment le soutien de premier choix évolue tour par tour
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
              <strong>Régret bayésien par tour</strong>
              <span className="text-muted ms-2" style={{ fontSize: '0.85rem' }}>
                — lignes plates = résistance au bandwagon ; lignes montantes = amplification
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
              <strong>Résumé de résistance</strong>
              <span className="text-muted ms-2" style={{ fontSize: '0.85rem' }}>
                — proportion de tours où le vainqueur diffère du tour 0
              </span>
            </Card.Header>
            <Card.Body className="p-0">
              <Table bordered size="sm" className="mb-0">
                <thead className="table-light">
                  <tr>
                    <th style={{ minWidth: 150 }}>Méthode</th>
                    <th className="text-center" style={{ minWidth: 120 }}>
                      Amplification
                    </th>
                    <th className="text-center">Verdict</th>
                    <th className="text-center" style={{ minWidth: 100 }}>
                      Vainqueur R0
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
