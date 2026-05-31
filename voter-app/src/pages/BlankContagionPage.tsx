import React, { useCallback, useState } from 'react';
import {
  Alert, Badge, Button, Card, Col, Container, Form, Row, Spinner,
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
import { useMetaTags } from '../hooks/useMetaTags';
import { $api } from '../api/hooks';

// ── Types ─────────────────────────────────────────────────────────────────────

type NetworkType = 'random' | 'clustered' | 'small-world';

interface ContagionResult {
  rounds: number[];
  blank_rate_by_round: number[];   // in %
  final_blank_rate: number;        // in %
  epidemic_threshold: number;      // R0
  reached_equilibrium: boolean;
  network_type: NetworkType;
  r0: number;
}

// ── Network descriptors ───────────────────────────────────────────────────────

const NETWORK_INFO: Record<NetworkType, { label: string; desc: string; color: string }> = {
  random: {
    label: 'Aléatoire',
    desc: 'Erdős-Rényi : chaque électeur est connecté aléatoirement à ~1% de la population.',
    color: '#1a56cc',
  },
  clustered: {
    label: 'Communautaire',
    desc: 'Modèle en blocs : 3 communautés avec davantage de liens internes qu\'externes.',
    color: '#b35c00',
  },
  'small-world': {
    label: 'Petit-monde',
    desc: 'Watts-Strogatz : clusters locaux avec quelques liens longue portée.',
    color: '#b71c1c',
  },
};

// ── R0 interpretation ─────────────────────────────────────────────────────────

function r0Badge(r0: number): { text: string; variant: string; color: string } {
  if (r0 < 0.5)   return { text: 'Très marginal',  variant: 'success', color: '#1b5e20' };
  if (r0 < 1.0)   return { text: 'En déclin',       variant: 'success', color: '#1b5e20' };
  if (r0 < 1.5)   return { text: 'Zone critique',   variant: 'warning', color: '#b35c00' };
  return               { text: 'Épidémique',        variant: 'danger',  color: '#b71c1c' };
}

function r0Interpretation(r0: number, finalRate: number, networkType: NetworkType): string {
  const net = NETWORK_INFO[networkType].label.toLowerCase();
  if (r0 < 1) {
    return `Dans ce réseau ${net} avec R₀ = ${r0.toFixed(2)} < 1, l'abstention contestataire (vote blanc) ` +
      `ne se propage pas durablement. Elle s'estompe progressivement jusqu'à un niveau résiduel ` +
      `de ${finalRate.toFixed(1)} %. Il s'agit d'un phénomène marginal sans dynamique collective.`;
  }
  if (finalRate > 30) {
    return `Dans ce réseau ${net} avec R₀ = ${r0.toFixed(2)} > 1, le vote blanc se propage ` +
      `et atteint ${finalRate.toFixed(1)} % de la population. ` +
      `C'est un signal fort de mécontentement structurel — une proportion significative de l'électorat ` +
      `rejette l'offre politique, pouvant invalider l'élection sous la règle THRESHOLD_30.`;
  }
  return `Dans ce réseau ${net} avec R₀ = ${r0.toFixed(2)} > 1, le vote blanc s'amplifie ` +
    `jusqu'à ${finalRate.toFixed(1)} % de l'électorat. La contagion sociale joue un rôle ` +
    `dans l'amplification du mécontentement — chaque électeur blanc peut en convaincre d'autres ` +
    `par conformité sociale ou désillusion partagée.`;
}

// ── BlankContagionPage ────────────────────────────────────────────────────────

const BlankContagionPage: React.FC = () => {
  useMetaTags({
    title: 'Contagion du vote blanc — Vote Lab',
    description: 'Modèle SIS de propagation sociale du vote blanc : R₀, seuil épidémique, réseaux.',
  });

  const [initialRate,   setInitialRate]   = useState(0.10);
  const [contagionRate, setContagionRate] = useState(0.30);
  const [recoveryRate,  setRecoveryRate]  = useState(0.15);
  const [numVoters,     setNumVoters]     = useState(300);
  const [numRounds,     setNumRounds]     = useState(20);
  const [networkType,   setNetworkType]   = useState<NetworkType>('random');

  const sim = $api.useMutation('post', '/api/v2/simulations/blank-contagion');
  const result: ContagionResult | null = (sim.data as ContagionResult | undefined) ?? null;
  const loading = sim.isPending;
  const error = sim.isError ? 'Erreur de simulation' : null;

  const r0 = contagionRate / Math.max(recoveryRate, 0.001);

  const runSimulation = useCallback(() => {
    sim.mutate({ body: {
      num_voters:         numVoters,
      initial_blank_rate: initialRate,
      contagion_rate:     contagionRate,
      recovery_rate:      recoveryRate,
      num_rounds:         numRounds,
      network_type:       networkType,
    } });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [numVoters, initialRate, contagionRate, recoveryRate, numRounds, networkType, sim]);

  // Chart data
  const chartData = result
    ? result.rounds.map((rnd, i) => ({
        round: rnd,
        'Vote blanc (%)': result.blank_rate_by_round[i],
      }))
    : [];

  const { text: r0Text, color: r0Color } = r0Badge(r0);
  const netInfo = NETWORK_INFO[networkType];

  return (
    <Container fluid className="py-4" style={{ maxWidth: 1200 }}>
      <h2 className="mb-1 fw-bold">⬜ Contagion du vote blanc</h2>
      <p className="text-muted mb-4" style={{ fontSize: '0.9rem' }}>
        Modèle épidémiologique SIS : le vote blanc se propage dans un réseau social d'électeurs.
        Chaque électeur "contaminé" peut convertir ses voisins ; chaque électeur blanc peut "guérir"
        et revenir au vote ordinaire.
      </p>

      <Row className="g-3">
        {/* ── Left — config ──────────────────────────────────────────────── */}
        <Col lg={3}>
          <Card className="mb-3">
            <Card.Header className="fw-semibold">⚙️ Paramètres</Card.Header>
            <Card.Body>
              <Form.Group className="mb-3">
                <Form.Label htmlFor="bc-voters" className="small mb-1">
                  Électeurs : <strong>{numVoters}</strong>
                </Form.Label>
                <Form.Range
                  id="bc-voters" min={50} max={800} step={50}
                  value={numVoters}
                  onChange={(e) => setNumVoters(Number(e.target.value))}
                />
              </Form.Group>

              <Form.Group className="mb-3">
                <Form.Label htmlFor="bc-init" className="small mb-1">
                  Taux initial de vote blanc : <strong>{(initialRate * 100).toFixed(0)} %</strong>
                </Form.Label>
                <Form.Range
                  id="bc-init" min={0} max={0.5} step={0.01}
                  value={initialRate}
                  onChange={(e) => setInitialRate(Number(e.target.value))}
                />
              </Form.Group>

              <Form.Group className="mb-3">
                <Form.Label htmlFor="bc-beta" className="small mb-1">
                  Taux de contagion β : <strong>{contagionRate.toFixed(2)}</strong>
                </Form.Label>
                <Form.Range
                  id="bc-beta" min={0} max={1} step={0.01}
                  value={contagionRate}
                  onChange={(e) => setContagionRate(Number(e.target.value))}
                />
              </Form.Group>

              <Form.Group className="mb-3">
                <Form.Label htmlFor="bc-gamma" className="small mb-1">
                  Taux de guérison γ : <strong>{recoveryRate.toFixed(2)}</strong>
                </Form.Label>
                <Form.Range
                  id="bc-gamma" min={0.01} max={1} step={0.01}
                  value={recoveryRate}
                  onChange={(e) => setRecoveryRate(Number(e.target.value))}
                />
              </Form.Group>

              <Form.Group className="mb-3">
                <Form.Label htmlFor="bc-rounds" className="small mb-1">
                  Rounds : <strong>{numRounds}</strong>
                </Form.Label>
                <Form.Range
                  id="bc-rounds" min={5} max={50} step={1}
                  value={numRounds}
                  onChange={(e) => setNumRounds(Number(e.target.value))}
                />
              </Form.Group>

              {/* Network type */}
              <div className="mb-3">
                <div className="small mb-2 fw-semibold">Type de réseau</div>
                <div className="d-flex flex-column gap-1">
                  {(Object.keys(NETWORK_INFO) as NetworkType[]).map((nt) => (
                    <Button
                      key={nt}
                      size="sm"
                      variant={networkType === nt ? 'primary' : 'outline-secondary'}
                      onClick={() => setNetworkType(nt)}
                      aria-pressed={networkType === nt}
                      style={{ textAlign: 'left', fontSize: '0.82rem' }}
                    >
                      {NETWORK_INFO[nt].label}
                    </Button>
                  ))}
                </div>
                <div className="text-muted mt-2" style={{ fontSize: '0.75rem', lineHeight: 1.4 }}>
                  {netInfo.desc}
                </div>
              </div>

              <Button
                variant="primary" className="w-100"
                onClick={runSimulation} disabled={loading}
              >
                {loading
                  ? <><Spinner size="sm" className="me-2" />Simulation…</>
                  : '▶ Simuler la contagion'}
              </Button>
            </Card.Body>
          </Card>

          {/* R0 live indicator */}
          <Card>
            <Card.Header className="py-2 fw-semibold" style={{ fontSize: '0.85rem' }}>
              📊 R₀ (seuil épidémique)
            </Card.Header>
            <Card.Body className="text-center py-3">
              <div style={{ fontSize: '2.8rem', fontWeight: 800, color: r0Color }}>
                {r0.toFixed(2)}
              </div>
              <Badge
                style={{ background: r0Color, fontSize: '0.8rem', padding: '4px 12px', marginTop: 4 }}
              >
                {r0Text}
              </Badge>
              <div className="text-muted mt-2" style={{ fontSize: '0.78rem' }}>
                R₀ = β / γ = {contagionRate.toFixed(2)} / {recoveryRate.toFixed(2)}
              </div>
              <hr className="my-2" />
              <div style={{ fontSize: '0.78rem', color: r0 < 1 ? '#1b5e20' : '#b71c1c' }}>
                {r0 < 1
                  ? '✓ Le vote blanc ne se propage pas — phénomène marginal'
                  : '⚠️ Le vote blanc s\'amplifie — mécontentement structurel'}
              </div>
            </Card.Body>
          </Card>
        </Col>

        {/* ── Centre — chart ─────────────────────────────────────────────── */}
        <Col lg={6}>
          <Card className="h-100">
            <Card.Header className="d-flex align-items-center justify-content-between">
              <strong>Évolution du vote blanc</strong>
              {result && (
                <div className="d-flex align-items-center gap-2">
                  <small className="text-muted">
                    Final : {result.final_blank_rate.toFixed(1)} %
                    {result.reached_equilibrium && ' · Équilibre atteint'}
                  </small>
                  {result.reached_equilibrium && (
                    <Badge bg="secondary" style={{ fontSize: '0.7rem' }}>Équilibre</Badge>
                  )}
                </div>
              )}
            </Card.Header>
            <Card.Body>
              {error && <Alert variant="danger">{error}</Alert>}

              {!result && !loading && (
                <Alert variant="info" style={{ fontSize: '0.88rem' }}>
                  Configurez les paramètres et cliquez sur <strong>Simuler</strong> pour
                  observer la propagation du vote blanc dans le réseau social.
                </Alert>
              )}

              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 16 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--bs-border-color, #dee2e6)" />
                  <XAxis
                    dataKey="round"
                    label={{ value: 'Round', position: 'insideBottom', offset: -10, fontSize: 11 }}
                    tick={{ fontSize: 11 }}
                  />
                  <YAxis
                    domain={[0, 100]}
                    tickFormatter={(v) => `${v}%`}
                    label={{ value: 'Vote blanc (%)', angle: -90, position: 'insideLeft', fontSize: 11 }}
                    tick={{ fontSize: 11 }}
                    width={56}
                  />
                  <Tooltip
                    formatter={(v: number) => [`${v.toFixed(1)} %`, 'Vote blanc']}
                    labelFormatter={(l) => `Round ${l}`}
                  />
                  <Legend verticalAlign="top" />

                  {/* Seuil THRESHOLD_30 */}
                  <ReferenceLine
                    y={30}
                    stroke="#f59e0b"
                    strokeDasharray="6 3"
                    strokeWidth={2}
                    label={{ value: 'Seuil 30%', position: 'right', fontSize: 11, fill: '#b45309' }}
                  />

                  <Line
                    type="monotone"
                    dataKey="Vote blanc (%)"
                    stroke={netInfo.color}
                    strokeWidth={2.5}
                    dot={{ r: 3 }}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>

              {result && (
                <div className="d-flex gap-3 mt-2 flex-wrap" style={{ fontSize: '0.82rem' }}>
                  <span className="text-muted">
                    R₀ simulé : <strong>{result.r0.toFixed(2)}</strong>
                  </span>
                  <span className="text-muted">
                    Taux initial : <strong>{(initialRate * 100).toFixed(0)} %</strong>
                  </span>
                  <span className="text-muted">
                    Taux final : <strong>{result.final_blank_rate.toFixed(1)} %</strong>
                  </span>
                </div>
              )}
            </Card.Body>
          </Card>
        </Col>

        {/* ── Right — interpretation ─────────────────────────────────────── */}
        <Col lg={3}>
          <Card className="mb-3">
            <Card.Header className="py-2 fw-semibold" style={{ fontSize: '0.85rem' }}>
              🔍 Interprétation
            </Card.Header>
            <Card.Body>
              {result ? (
                <p className="mb-0" style={{ fontSize: '0.85rem', lineHeight: 1.6 }}>
                  {r0Interpretation(result.r0, result.final_blank_rate, result.network_type)}
                </p>
              ) : (
                <p className="text-muted mb-0" style={{ fontSize: '0.85rem' }}>
                  Lancez une simulation pour obtenir une interprétation.
                </p>
              )}
            </Card.Body>
          </Card>

          {/* Lexicon */}
          <Card>
            <Card.Header className="py-2 fw-semibold" style={{ fontSize: '0.85rem' }}>
              📖 Lexique SIS
            </Card.Header>
            <Card.Body style={{ fontSize: '0.82rem' }}>
              {[
                { term: 'S (Susceptible)', def: 'Électeur qui vote normalement et peut devenir un électeur blanc.' },
                { term: 'I (Infecté)', def: 'Électeur qui vote blanc et peut "contaminer" ses voisins.' },
                { term: 'β (contagion)', def: 'Probabilité qu\'un contact infecté convertisse un électeur sain.' },
                { term: 'γ (guérison)', def: 'Probabilité qu\'un électeur blanc revienne au vote ordinaire.' },
                { term: 'R₀ = β/γ', def: 'Seuil épidémique. R₀ < 1 : extinction. R₀ > 1 : propagation.' },
                { term: 'Seuil 30 %', def: 'Si le vote blanc dépasse 30 %, l\'élection est invalidée (règle THRESHOLD_30).' },
              ].map(({ term, def }) => (
                <div key={term} className="mb-2">
                  <div className="fw-semibold" style={{ color: 'var(--bs-primary, #0d6efd)' }}>{term}</div>
                  <div className="text-muted">{def}</div>
                </div>
              ))}
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  );
};

export default BlankContagionPage;
