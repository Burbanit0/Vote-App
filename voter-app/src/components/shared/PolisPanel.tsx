/**
 * PolisPanel — Pol.is-style consensus simulation with candidate evaluation.
 * Compares the "Pol.is winner" (most aligned with consensus) against the
 * classical election winner. Shows consensus, polarizing, and silent-majority
 * statements via PCA scatter + statement table.
 */
import React, { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, Badge, Button, Col, Form, Row, Spinner, Table } from 'react-bootstrap';
import { useElection } from '../../context/ElectionContext';
import { $api } from '../../api/hooks';

// ── Types ─────────────────────────────────────────────────────────────────────

interface PolisCluster {
  id:     number;
  size:   number;
  label:  string;
  center: { x: number; y: number };
  votes:  Record<number, number>;
}

interface PolisStatement {
  text:             string;
  global_approval:  number;
  is_consensus:     boolean;
  is_polarizing:    boolean;
  cluster_approvals: number[];
}

interface ParticipantPos { id: number; x_pca: number; y_pca: number; cluster_id: number; }

interface PolisData {
  clusters:              PolisCluster[];
  statements:            PolisStatement[];
  participant_positions: ParticipantPos[];
  polis_winner:          string;
  election_winner:       string;
  winners_agree:         boolean;
  consensus_count:       number;
  polarizing_count:      number;
  silent_majority_count: number;
  candidate_scores:      Record<string, number>;
  pedagogical_note:      string;
}

// ── Palette ───────────────────────────────────────────────────────────────────

const CLUSTER_COLORS = ['#005CAB', '#C8590A', '#007A33', '#9b59b6', '#e67e22'];
function clusterColor(id: number): string {
  return CLUSTER_COLORS[id % CLUSTER_COLORS.length];
}

// ── PCA Scatter ───────────────────────────────────────────────────────────────

const W = 460, H = 280, PAD = 28;

interface ScatterProps {
  positions: ParticipantPos[];
  clusters:  PolisCluster[];
}

const PolisScatterSVG: React.FC<ScatterProps> = ({ positions, clusters }) => {
  if (!positions.length) return null;
  const xs = positions.map((p) => p.x_pca), ys = positions.map((p) => p.y_pca);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const spanX = (maxX - minX) || 1, spanY = (maxY - minY) || 1;
  const px = (x: number) => PAD + ((x - minX) / spanX) * (W - 2 * PAD);
  const py = (y: number) => H - PAD - ((y - minY) / spanY) * (H - 2 * PAD);
  const sample = positions.length > 200
    ? positions.filter((_, i) => i % Math.ceil(positions.length / 200) === 0)
    : positions;

  return (
    <svg data-testid="polis-scatter-svg" width="100%" viewBox={`0 0 ${W} ${H}`}>
      {/* Cluster labels */}
      {clusters.map((c) => (
        <text key={c.id}
          x={px(clusters.find((cc) => cc.id === c.id)?.center.x ?? 0) ?? W / 2}
          y={py(clusters.find((cc) => cc.id === c.id)?.center.y ?? 0) ?? H / 2}
          textAnchor="middle" style={{ fontSize: 9, fill: clusterColor(c.id), fontWeight: 600 }}>
          {c.label}
        </text>
      ))}
      {/* Dots */}
      {sample.map((p) => (
        <circle key={p.id} cx={px(p.x_pca)} cy={py(p.y_pca)} r={3}
          fill={clusterColor(p.cluster_id)} opacity={0.6} />
      ))}
    </svg>
  );
};

// ── Taiwan examples sidebar ───────────────────────────────────────────────────

const TAIWAN_EXAMPLES = [
  { stmt: "Les chauffeurs VTC doivent être déclarés officiellement", result: '92% dans tous les clusters → Devenu loi', type: 'consensus' },
  { stmt: "Uber doit être interdit", result: 'Rejeté par 2 clusters sur 3 → Pas de consensus', type: 'polarizing' },
  { stmt: "La tarification dynamique est équitable", result: '71% global mais 34% chez les syndicats → Majorité silencieuse', type: 'silent' },
];

const TaiwanSidebar: React.FC<{ t: (k: string) => string }> = ({ t }) => (
  <div data-testid="taiwan-examples">
    <div className="fw-semibold mb-2" style={{ fontSize: '0.82rem' }}>🇹🇼 {t('polis.taiwanTitle')}</div>
    {TAIWAN_EXAMPLES.map((ex, i) => (
      <div key={i} className="border rounded p-2 mb-2"
        style={{ fontSize: '0.72rem', background: '#f8f9fa' }}>
        <div style={{ fontStyle: 'italic', color: '#495057' }}>"{ex.stmt}"</div>
        <div className="mt-1">
          <Badge bg={ex.type === 'consensus' ? 'success' : ex.type === 'polarizing' ? 'danger' : 'warning'}
            text={ex.type === 'silent' ? 'dark' : undefined}
            style={{ fontSize: '0.6rem' }}>
            {t(`polis.${ex.type}`)}
          </Badge>{' '}
          <span className="text-muted">{ex.result}</span>
        </div>
      </div>
    ))}
  </div>
);

// ── Statement table ───────────────────────────────────────────────────────────

interface StmtTableProps {
  statements: PolisStatement[];
  clusters:   PolisCluster[];
  filter:     'all' | 'consensus' | 'polarizing';
  t:          (k: string) => string;
}

const StatementTable: React.FC<StmtTableProps> = ({ statements, clusters, filter, t }) => {
  const visible = statements.filter((s) => {
    if (filter === 'consensus')  return s.is_consensus;
    if (filter === 'polarizing') return s.is_polarizing;
    return true;
  });

  return (
    <Table size="sm" hover className="mb-2" data-testid="statement-table">
      <thead>
        <tr>
          <th style={{ fontSize: '0.75rem' }}>{t('polis.statement')}</th>
          <th style={{ fontSize: '0.75rem' }}>{t('polis.global')}</th>
          {clusters.map((c) => (
            <th key={c.id} style={{ fontSize: '0.72rem', color: clusterColor(c.id) }}>
              {c.label}
            </th>
          ))}
          <th style={{ fontSize: '0.75rem' }}>{t('polis.status')}</th>
        </tr>
      </thead>
      <tbody>
        {visible.map((s, i) => (
          <tr key={i} style={{
            background: s.is_consensus ? '#f0fff4' : s.is_polarizing ? '#fff5f5' : undefined,
          }}>
            <td style={{ fontSize: '0.75rem', maxWidth: 200 }}>{s.text}</td>
            <td style={{ fontSize: '0.75rem' }}>{Math.round(s.global_approval * 100)}%</td>
            {s.cluster_approvals.map((rate, ci) => (
              <td key={ci} style={{ fontSize: '0.75rem', color: clusterColor(ci) }}>
                {Math.round(rate * 100)}%
              </td>
            ))}
            <td>
              {s.is_consensus && <Badge bg="success" style={{ fontSize: '0.6rem' }}>🟢 {t('polis.consensus')}</Badge>}
              {s.is_polarizing && <Badge bg="danger"  style={{ fontSize: '0.6rem' }}>🔴 {t('polis.polarizing')}</Badge>}
              {!s.is_consensus && !s.is_polarizing && (
                <Badge bg="secondary" style={{ fontSize: '0.6rem' }}>⚪ {t('polis.mitigated')}</Badge>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
};

// ── Main panel ────────────────────────────────────────────────────────────────

const PolisPanel: React.FC = () => {
  const { t }      = useTranslation();
  const { config } = useElection();

  const [numClusters, setNumClusters] = useState(3);
  const [threshold,   setThreshold]   = useState(0.80);
  const [ideology,    setIdeology]    = useState('random');
  const [stmtFilter,  setStmtFilter]  = useState<'all'|'consensus'|'polarizing'>('all');
  const sim = $api.useMutation('post', '/api/v2/tech/polis');
  const data: PolisData | null = (sim.data as PolisData | undefined) ?? null;
  const loading = sim.isPending;
  const error = sim.isError ? t('polis.error') : null;

  const runSimulation = useCallback(() => {
    sim.mutate({ body: {
      candidates:                config.candidates.map((c) => ({ name: c.name, x: c.x, y: c.y })),
      num_participants:          config.num_voters,
      ideology,
      seed:                      config.seed,
      num_clusters:              numClusters,
      min_consensus_threshold:   threshold,
      method_to_compare:        'plurality',
    } });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config, numClusters, threshold, ideology, t, sim]);

  return (
    <div>
      {/* Controls */}
      <Row className="g-2 mb-3 align-items-end">
        <Col xs={6} md={3}>
          <Form.Label className="small mb-0">{t('polis.ideology')}</Form.Label>
          <Form.Select size="sm" value={ideology}
            data-testid="ideology-select"
            onChange={(e) => setIdeology(e.target.value)}>
            <option value="random">{t('polis.ideologyRandom')}</option>
            <option value="polarized">{t('polis.ideologyPolarized')}</option>
            <option value="centrist">{t('polis.ideologyCentrist')}</option>
          </Form.Select>
        </Col>
        <Col xs={6} md={2}>
          <Form.Label className="small mb-0">{t('polis.clusters')}</Form.Label>
          <Form.Control type="number" size="sm" min={1} max={5} value={numClusters}
            data-testid="clusters-input"
            onChange={(e) => setNumClusters(Math.max(1, Math.min(5, Number(e.target.value))))} />
        </Col>
        <Col xs={6} md={3}>
          <Form.Label className="small mb-0">
            {t('polis.threshold')}: <strong>{Math.round(threshold * 100)}%</strong>
          </Form.Label>
          <Form.Range min={0} max={1} step={0.05} value={threshold}
            data-testid="threshold-slider"
            onChange={(e) => setThreshold(Number(e.target.value))} />
        </Col>
        <Col xs="auto">
          <Button variant="primary" onClick={runSimulation} disabled={loading}
            data-testid="simulate-btn">
            {loading ? <Spinner size="sm" animation="border" /> : t('polis.run')}
          </Button>
        </Col>
      </Row>

      {!data && !loading && !error && (
        <Alert variant="info" role="alert">{t('polis.prompt')}</Alert>
      )}
      {error && <Alert variant="danger">{error}</Alert>}

      {data && (
        <Row className="g-3">
          {/* Main content */}
          <Col xs={12} md={8}>
            {/* Winner comparison */}
            <div
              className={`d-flex align-items-center gap-3 p-3 rounded mb-3 ${
                data.winners_agree ? 'border border-success' : 'border border-warning'
              }`}
              data-testid="winner-comparison"
            >
              <div className="text-center">
                <div className="text-muted" style={{ fontSize: '0.72rem' }}>🌐 Pol.is</div>
                <Badge bg="primary" style={{ fontSize: '0.85rem', padding: '6px 12px' }}
                  data-testid="polis-winner-badge">
                  {data.polis_winner}
                </Badge>
              </div>
              <span style={{ fontSize: '1.2rem', color: data.winners_agree ? '#198754' : '#fd7e14' }}>
                {data.winners_agree ? '=' : '≠'}
              </span>
              <div className="text-center">
                <div className="text-muted" style={{ fontSize: '0.72rem' }}>🗳 Vote classique</div>
                <Badge bg="secondary" style={{ fontSize: '0.85rem', padding: '6px 12px' }}
                  data-testid="election-winner-badge">
                  {data.election_winner}
                </Badge>
              </div>
              {!data.winners_agree && (
                <Alert variant="warning" className="d-inline-block py-1 px-2 mb-0"
                  data-testid="winners-diverge-alert" style={{ fontSize: '0.75rem' }}>
                  {t('polis.winnersDisagree')}
                </Alert>
              )}
            </div>

            {/* Stats badges */}
            <div className="d-flex flex-wrap gap-2 mb-3">
              <Badge bg="success" data-testid="consensus-count-badge">
                🟢 {data.consensus_count} {t('polis.consensus')}
              </Badge>
              <Badge bg="danger" data-testid="polarizing-count-badge">
                🔴 {data.polarizing_count} {t('polis.polarizing')}
              </Badge>
              <Badge bg="warning" text="dark" data-testid="silent-majority-badge">
                ⚪ {data.silent_majority_count} {t('polis.silent_majority')}
              </Badge>
            </div>

            {/* Scatter plot */}
            <div className="border rounded mb-3" style={{ background: '#f8f9fa', overflow: 'hidden' }}>
              <PolisScatterSVG
                positions={data.participant_positions}
                clusters={data.clusters}
              />
            </div>

            {/* Statement filter */}
            <div className="d-flex gap-2 mb-2">
              {(['all', 'consensus', 'polarizing'] as const).map((f) => (
                <Button key={f} size="sm"
                  variant={stmtFilter === f ? 'primary' : 'outline-secondary'}
                  data-testid={`filter-${f}`}
                  onClick={() => setStmtFilter(f)}>
                  {t(`polis.filter_${f}`)}
                </Button>
              ))}
            </div>

            {/* Statement table */}
            <StatementTable
              statements={data.statements}
              clusters={data.clusters}
              filter={stmtFilter}
              t={t}
            />

            {/* Pedagogical note */}
            <Alert variant="secondary" style={{ fontSize: '0.8rem' }}>
              <strong>{t('polis.noteTitle')}</strong> {data.pedagogical_note}
            </Alert>
          </Col>

          {/* Sidebar */}
          <Col xs={12} md={4}>
            <TaiwanSidebar t={t} />
          </Col>
        </Row>
      )}
    </div>
  );
};

export default PolisPanel;
