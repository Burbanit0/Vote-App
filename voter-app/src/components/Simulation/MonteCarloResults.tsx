import React, { useMemo, useState } from 'react';
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  Form,
  ProgressBar,
  Row,
  Spinner,
  Table,
} from 'react-bootstrap';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ErrorBar,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { MonteCarloResult } from '../../types';
import { getMonteCarlo, MonteCarloParams } from '../../services/simulationCompareApi';
import ResponsiveTable from '../shared/ResponsiveTable';
import SkeletonCard from '../shared/SkeletonCard';
import { useChartTheme } from '../../hooks/useChartTheme';

// ── Constants ──────────────────────────────────────────────────────────────

const METHOD_LABELS: Record<string, string> = {
  plurality:            'Pluralité',
  two_round:            'Deux tours',
  borda:                'Borda',
  approval:             'Approbation',
  irv:                  'IRV',
  coombs:               "Coombs'",
  bucklin:              'Bucklin',
  minimax:              'Minimax',
  schulze:              'Schulze',
  simple_score:         'Score simple',
  star_voting:          'STAR',
  median_voting:        'Score médian',
  mean_median_hybrid:   'Moy.-Médiane',
  variance_based:       'Variance',
};

const IDEOLOGY_OPTIONS = [
  { value: 'random',       label: 'Aléatoire' },
  { value: 'centrist',     label: 'Centriste' },
  { value: 'polarized',    label: 'Polarisée' },
  { value: 'left_skewed',  label: 'Majorité gauche' },
  { value: 'right_skewed', label: 'Majorité droite' },
];

const CANDIDATE_PALETTE = ['#4e79a7', '#f28e2b', '#e15759', '#76b7b2', '#59a14f', '#edc948'];

// ── Helpers ────────────────────────────────────────────────────────────────

function cellStyle(rate: number, isDark: boolean): React.CSSProperties {
  if (isDark) {
    if (rate >= 0.8) return { backgroundColor: '#1a3a2a', color: '#75b798' };
    if (rate >= 0.5) return { backgroundColor: '#332b00', color: '#c0964e' };
    return { backgroundColor: '#3a1a1e', color: '#ea868f' };
  }
  if (rate >= 0.8) return { backgroundColor: '#d4edda', color: '#155724' };
  if (rate >= 0.5) return { backgroundColor: '#fff3cd', color: '#856404' };
  return { backgroundColor: '#f8d7da', color: '#721c24' };
}

function parseAgreementKey(key: string): [string, string] {
  const idx = key.indexOf('|');
  return [key.slice(0, idx), key.slice(idx + 1)];
}

// ── Component ──────────────────────────────────────────────────────────────

interface Props {
  baseParams: { num_voters?: number; candidates?: string[]; ideology_distribution?: string };
}

const MonteCarloResults: React.FC<Props> = ({ baseParams }) => {
  const ct = useChartTheme();
  const [sortByRegret, setSortByRegret] = useState(false);
  const [numRuns, setNumRuns] = useState(100);
  const [numVoters, setNumVoters] = useState(baseParams.num_voters ?? 150);
  const [ideologyDist, setIdeologyDist] = useState(baseParams.ideology_distribution ?? 'random');
  const [result, setResult] = useState<MonteCarloResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runMC = async () => {
    setLoading(true);
    setError(null);
    try {
      const params: MonteCarloParams = {
        num_runs: numRuns,
        num_voters: numVoters,
        candidates: baseParams.candidates,
        ideology_distribution: ideologyDist,
      };
      setResult(await getMonteCarlo(params));
    } catch {
      setError('Simulation Monte Carlo échouée. Vérifiez que le backend est démarré.');
    } finally {
      setLoading(false);
    }
  };

  // ── Derived ────────────────────────────────────────────────────────────

  const methodNames = useMemo(() => (result ? Object.keys(result.methods) : []), [result]);

  // All unique candidate names seen across winner distributions
  const candidateNames = useMemo(() => {
    if (!result) return [] as string[];
    const names = new Set<string>();
    Object.values(result.methods).forEach((m) =>
      Object.keys(m.winner_distribution).forEach((c) => names.add(c))
    );
    return [...names];
  }, [result]);

  const colorMap = useMemo(
    () => Object.fromEntries(candidateNames.map((c, i) => [c, CANDIDATE_PALETTE[i % CANDIDATE_PALETTE.length]])),
    [candidateNames]
  );

  // Bar chart data: regret mean + error value, optionally sorted
  const regretBarData = useMemo(() => {
    const data = methodNames.map((m) => {
      const s = result!.methods[m];
      const ci = s.bayesian_regret_ci_95;
      const mean = s.bayesian_regret_mean ?? 0;
      const errorVal = ci[1] != null ? ci[1] - mean : 0;
      return { method: METHOD_LABELS[m] ?? m, regret: mean, errorVal };
    });
    return sortByRegret ? [...data].sort((a, b) => a.regret - b.regret) : data;
  }, [result, methodNames, sortByRegret]);

  // Stability table sorted ascending (most stable first)
  const stabilityRows = useMemo(
    () =>
      methodNames
        .map((m) => {
          const s = result!.methods[m];
          const pct = s.most_common_winner
            ? (s.winner_distribution[s.most_common_winner] ?? 0)
            : 0;
          return {
            method: m,
            winner: s.most_common_winner,
            pct,
            stability: s.winner_stability,
            compliance: s.condorcet_compliance_rate,
          };
        })
        .sort((a, b) => a.stability - b.stability),
    [result, methodNames]
  );

  // Agreement matrix row/col order
  const agreementMethodNames = useMemo(() => {
    if (!result) return [] as string[];
    const seen = new Set<string>();
    Object.keys(result.inter_method_agreement).forEach((key) => {
      const [a, b] = parseAgreementKey(key);
      seen.add(a);
      seen.add(b);
    });
    return [...seen];
  }, [result]);

  const getAgreement = (a: string, b: string): number | null => {
    if (!result) return null;
    if (a === b) return 1;
    return result.inter_method_agreement[`${a}|${b}`] ?? result.inter_method_agreement[`${b}|${a}`] ?? null;
  };

  // ── Render ─────────────────────────────────────────────────────────────

  return (
    <div>
      {/* Config */}
      <Card className="mb-4">
        <Card.Header><strong>Configuration Monte Carlo</strong></Card.Header>
        <Card.Body>
          <Row className="g-3 align-items-end">
            <Col md={3}>
              <Form.Label className="small mb-1">
                Simulations : <strong>{numRuns}</strong>
              </Form.Label>
              <Form.Range
                min={20} max={500} step={10} value={numRuns}
                onChange={(e) => setNumRuns(Number(e.target.value))}
              />
            </Col>
            <Col md={2}>
              <Form.Label className="small mb-1">Électeurs / simulation</Form.Label>
              <Form.Control
                size="sm" type="number" min={50} max={500} value={numVoters}
                onChange={(e) => setNumVoters(Number(e.target.value))}
              />
            </Col>
            <Col md={3}>
              <Form.Label className="small mb-1">Distribution</Form.Label>
              <Form.Select
                size="sm" value={ideologyDist}
                onChange={(e) => setIdeologyDist(e.target.value)}
              >
                {IDEOLOGY_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </Form.Select>
            </Col>
            <Col md={2}>
              <Button variant="primary" size="sm" className="w-100" onClick={runMC} disabled={loading}>
                {loading
                  ? <><Spinner size="sm" className="me-2" />Simulation…</>
                  : 'Lancer Monte Carlo'}
              </Button>
            </Col>
          </Row>
          <p className="text-muted small mt-2 mb-0">
            Utilise la liste de candidats du Scénario A. La vulnérabilité stratégique est ignorée pour la vitesse.
            Chaque simulation génère une population fraîche — les résultats montrent des distributions statistiques.
          </p>
        </Card.Body>
      </Card>

      {error && <Alert variant="danger">{error}</Alert>}

      {loading && (
        <Row className="g-3 mb-2">
          {[220, 300, 200].map((h, i) => <Col key={i} md={4}><SkeletonCard height={h} /></Col>)}
        </Row>
      )}

      {!result && !loading && (
        <Alert variant="info">
          Configurez ci-dessus et cliquez sur <strong>Lancer Monte Carlo</strong>.
          ~{Math.round(numRuns * numVoters / 1000 * 2)} sec estimées.
        </Alert>
      )}

      {result && (
        <>
          <Alert variant="secondary" className="py-2 mb-4">
            <strong>{result.num_runs} simulations</strong> ·{' '}
            {result.num_voters_per_run} électeurs/sim ·{' '}
            Vainqueur de Condorcet dans{' '}
            <strong>{(result.condorcet_winner_exists_rate * 100).toFixed(0)}%</strong>{' '}
            des simulations
          </Alert>

          {/* 1. Regret bar chart with CI error bars */}
          <Card className="mb-4">
            <Card.Header className="d-flex align-items-center justify-content-between flex-wrap gap-2">
              <div>
                <strong>Régret bayésien avec intervalles de confiance à 95%</strong>
                <span className="text-muted ms-2" style={{ fontSize: '0.85rem' }}>
                  — barres d'erreur = ±1.96 σ / √n
                </span>
              </div>
              <Button
                size="sm"
                variant={sortByRegret ? 'secondary' : 'outline-secondary'}
                onClick={() => setSortByRegret(!sortByRegret)}
                style={{ fontSize: '0.78rem' }}
              >
                {sortByRegret ? '↕ Ordre original' : '↑ Trier par regret'}
              </Button>
            </Card.Header>
            <Card.Body>
              <ResponsiveContainer width="100%" height={380}>
                <BarChart data={regretBarData} margin={{ top: 10, bottom: 80, left: 10, right: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} />
                  <XAxis
                    dataKey="method"
                    tick={{ fontSize: 10, fill: ct.tickFill }}
                    angle={-45}
                    textAnchor="end"
                    interval={0}
                  />
                  <YAxis tick={{ fontSize: 10, fill: ct.tickFill }} />
                  <Tooltip formatter={(v: number) => v.toFixed(4)} contentStyle={ct.tooltipStyle} />
                  <Bar dataKey="regret" name="Régret bayésien" fill="#4e79a7">
                    {regretBarData.map((_, i) => (
                      <Cell key={i} fill="#4e79a7" />
                    ))}
                    <ErrorBar
                      dataKey="errorVal"
                      width={6}
                      strokeWidth={3}
                      stroke="#e15759"
                      direction="y"
                    />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Card.Body>
          </Card>

          {/* 2. Inter-method agreement heatmap */}
          <Card className="mb-4">
            <Card.Header>
              <strong>Accord inter-méthodes</strong>
              <span className="text-muted ms-2" style={{ fontSize: '0.85rem' }}>
                — % des simulations où les deux méthodes élisent le même vainqueur
              </span>
            </Card.Header>
            <Card.Body>
              <div className="d-flex gap-3 mb-3">
                {[
                  { bg: '#d4edda', color: '#155724', label: '≥ 80%' },
                  { bg: '#fff3cd', color: '#856404', label: '50–80%' },
                  { bg: '#f8d7da', color: '#721c24', label: '< 50%' },
                ].map(({ bg, color, label }) => (
                  <span key={label} className="d-flex align-items-center gap-1">
                    <span style={{ display: 'inline-block', width: 14, height: 14, backgroundColor: bg, border: `1px solid ${color}`, borderRadius: 2 }} />
                    <small style={{ color }}>{label}</small>
                  </span>
                ))}
              </div>
              <ResponsiveTable>
                <Table bordered size="sm" className="text-center" style={{ minWidth: 400 }}>
                  <thead className="table-light">
                    <tr>
                      <th style={{ minWidth: 120, textAlign: 'left' }}>Méthode</th>
                      {agreementMethodNames.map((m) => (
                        <th key={m} style={{ minWidth: 80, fontSize: '0.75rem' }}>
                          {METHOD_LABELS[m] ?? m}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {agreementMethodNames.map((rowMethod) => (
                      <tr key={rowMethod}>
                        <td className="text-start ps-1 fw-semibold" style={{ fontSize: '0.8rem' }}>
                          {METHOD_LABELS[rowMethod] ?? rowMethod}
                        </td>
                        {agreementMethodNames.map((colMethod) => {
                          const rate = getAgreement(rowMethod, colMethod);
                          if (rowMethod === colMethod) {
                            return (
                              <td key={colMethod} style={{ backgroundColor: '#e9ecef', color: '#6c757d' }}>
                                —
                              </td>
                            );
                          }
                          return (
                            <td key={colMethod} style={rate != null ? cellStyle(rate, ct.isDark) : undefined}>
                              {rate != null ? `${(rate * 100).toFixed(0)}%` : '?'}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </Table>
              </ResponsiveTable>
            </Card.Body>
          </Card>

          {/* 3. Stability table */}
          <Card>
            <Card.Header>
              <strong>Stabilité du vainqueur</strong>
              <span className="text-muted ms-2" style={{ fontSize: '0.85rem' }}>
                — triée du plus stable au moins stable (entropie de Shannon minimale)
              </span>
            </Card.Header>
            <Card.Body className="p-0">
              <Table bordered size="sm" className="mb-0">
                <thead className="table-light">
                  <tr>
                    <th style={{ minWidth: 150 }}>Méthode</th>
                    <th className="text-center">Vainqueur le plus fréquent</th>
                    <th className="text-center" style={{ minWidth: 80 }}>% des sim.</th>
                    <th style={{ minWidth: 160 }}>Stabilité</th>
                    <th className="text-center" title="% des simulations où le vainqueur de Condorcet (quand il existe) a été élu">
                      Conformité Condorcet
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {stabilityRows.map(({ method, winner, pct, stability, compliance }) => (
                    <tr key={method}>
                      <td className="fw-semibold ps-2">{METHOD_LABELS[method] ?? method}</td>
                      <td className="text-center">
                        {winner ? (
                          <Badge style={{ backgroundColor: colorMap[winner] ?? '#999', fontSize: '0.75rem' }}>
                            {winner}
                          </Badge>
                        ) : (
                          <span className="text-muted">—</span>
                        )}
                      </td>
                      <td className="text-center">
                        <strong>{(pct * 100).toFixed(0)}%</strong>
                      </td>
                      <td>
                        <div className="d-flex align-items-center gap-2">
                          <ProgressBar
                            now={(1 - stability) * 100}
                            variant={stability < 0.25 ? 'success' : stability < 0.6 ? 'warning' : 'danger'}
                            style={{ flex: 1, height: 8 }}
                          />
                          <small className="text-muted" style={{ minWidth: 36 }}>
                            {(stability * 100).toFixed(0)}%
                          </small>
                        </div>
                      </td>
                      <td className="text-center">
                        {compliance != null
                          ? `${(compliance * 100).toFixed(0)}%`
                          : <span className="text-muted small">N/A</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </Card.Body>
          </Card>
        </>
      )}
    </div>
  );
};

export default MonteCarloResults;
