/**
 * ConvictionVotingPanel — simulates Polkadot-style Conviction Voting.
 * vote_weight = tokens × multiplier(lock_days)
 * Compares conviction-weighted results with plain 1-token-1-vote.
 */
import React, { useCallback, useRef, useState } from 'react';
import axios from 'axios';
import { useTranslation } from 'react-i18next';
import {
  Alert, Badge, Button, Col, Form, Row, Spinner, Table,
} from 'react-bootstrap';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, Legend, CartesianGrid,
  ResponsiveContainer, Cell,
} from 'recharts';
import { useElection } from '../../context/ElectionContext';
import { apiPath } from '../../api/apiVersion';

const API = process.env.REACT_APP_API_URL ?? 'http://localhost:4434';

const LOCK_OPTIONS = [0, 7, 14, 28, 56, 112, 224];
const MULTIPLIERS: Record<number, number> = {
  0: 0.1, 7: 1, 14: 2, 28: 3, 56: 4, 112: 5, 224: 6,
};

// ── Types ─────────────────────────────────────────────────────────────────────

interface ProposalStat {
  name:                        string;
  conviction_score:            number;
  token_score:                 number;
  avg_conviction_of_supporters: number;
  avg_tokens_of_supporters:    number;
}

interface VoterDot {
  id:               number;
  tokens:           number;
  lock_days:        number;
  conviction_mult:  number;
  conviction_weight: number;
  choice:           string;
}

interface ConvictionData {
  conviction_winner: string;
  token_winner:      string;
  winner_changed:    boolean;
  proposals:         ProposalStat[];
  voter_scatter:     VoterDot[];
  voter_stats: {
    gini_tokens:          number;
    gini_conviction:      number;
    whale_pct_tokens:     number;
    whale_pct_conviction: number;
  };
  pedagogical_note: string;
}

// ── Palette ───────────────────────────────────────────────────────────────────

const PROP_COLORS = ['#005CAB', '#C8590A', '#007A33', '#6c757d', '#9b59b6', '#e67e22', '#17a2b8', '#e83e8c'];
function propColor(name: string, names: string[]): string {
  return PROP_COLORS[names.indexOf(name) % PROP_COLORS.length] ?? '#888';
}

// ── Scatter SVG ───────────────────────────────────────────────────────────────

const SVG_W = 520, SVG_H = 240, PAD_L = 60, PAD_R = 20, PAD_T = 10, PAD_B = 40;

interface ScatterProps {
  dots:          VoterDot[];
  proposalNames: string[];
  t:             (k: string) => string;
}

const ConvictionScatter: React.FC<ScatterProps> = ({ dots, proposalNames, t }) => {
  if (!dots.length) return null;

  const maxTokens = Math.max(...dots.map((d) => d.tokens));
  const maxCW     = Math.max(...dots.map((d) => d.conviction_weight));

  const xScale = (tokens: number) =>
    PAD_L + (Math.log(tokens + 1) / Math.log(maxTokens + 1)) * (SVG_W - PAD_L - PAD_R);

  const lockYMap: Record<number, number> = {};
  LOCK_OPTIONS.forEach((d, i) => {
    lockYMap[d] = PAD_T + ((LOCK_OPTIONS.length - 1 - i) / (LOCK_OPTIONS.length - 1)) *
                  (SVG_H - PAD_T - PAD_B);
  });

  const rScale = (cw: number) =>
    Math.max(2, Math.sqrt(cw / maxCW) * 12);

  // Sample to max 200 dots for performance
  const sample = dots.length > 200 ? dots.filter((_, i) => i % Math.ceil(dots.length / 200) === 0) : dots;

  return (
    <svg
      data-testid="conviction-scatter-svg"
      width="100%"
      viewBox={`0 0 ${SVG_W} ${SVG_H}`}
      style={{ display: 'block' }}
    >
      {/* Y axis labels (lock days) */}
      {LOCK_OPTIONS.map((d) => (
        <text key={d} x={PAD_L - 4} y={lockYMap[d] + 4} textAnchor="end"
          style={{ fontSize: 9, fill: '#6c757d' }}>
          {d}j ×{MULTIPLIERS[d]}
        </text>
      ))}

      {/* X axis label */}
      <text x={SVG_W / 2} y={SVG_H - 4} textAnchor="middle"
        style={{ fontSize: 10, fill: '#6c757d' }}>
        {t('conviction.scatterX')} (log)
      </text>
      <text x={8} y={SVG_H / 2} textAnchor="middle" transform={`rotate(-90,8,${SVG_H / 2})`}
        style={{ fontSize: 10, fill: '#6c757d' }}>
        {t('conviction.scatterY')}
      </text>

      {/* Horizontal grid */}
      {LOCK_OPTIONS.map((d) => (
        <line key={d}
          x1={PAD_L} y1={lockYMap[d]} x2={SVG_W - PAD_R} y2={lockYMap[d]}
          stroke="#f0f0f0" strokeWidth={1} />
      ))}

      {/* Dots */}
      {sample.map((dot) => {
        const cx = xScale(dot.tokens);
        const cy = lockYMap[dot.lock_days] ?? SVG_H / 2;
        const r  = rScale(dot.conviction_weight);
        const color = propColor(dot.choice, proposalNames);
        return (
          <circle key={dot.id} cx={cx} cy={cy} r={r}
            fill={color} opacity={0.6} />
        );
      })}
    </svg>
  );
};

// ── Comparison chart ──────────────────────────────────────────────────────────

interface CompareChartProps {
  proposals:     ProposalStat[];
  proposalNames: string[];
  t:             (k: string) => string;
}

const CompareChart: React.FC<CompareChartProps> = ({ proposals, proposalNames, t }) => {
  const chartData = proposals.map((p) => ({
    name:       p.name.length > 14 ? p.name.slice(0, 12) + '…' : p.name,
    conviction: Math.round(p.conviction_score),
    token:      Math.round(p.token_score),
  }));

  return (
    <div data-testid="compare-bar-chart">
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={chartData} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="name" tick={{ fontSize: 10 }} />
          <YAxis tick={{ fontSize: 10 }} />
          <Tooltip />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Bar dataKey="conviction" name={t('conviction.cvScore')} fill="#6610f2">
            {chartData.map((_, i) => (
              <Cell key={i} fill={PROP_COLORS[i % PROP_COLORS.length]} />
            ))}
          </Bar>
          <Bar dataKey="token" name={t('conviction.tokenScore')} fill="#adb5bd" opacity={0.7} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

// ── Main panel ────────────────────────────────────────────────────────────────

const ConvictionVotingPanel: React.FC = () => {
  const { t }      = useTranslation();
  const { config } = useElection();

  const [cvDist,      setCvDist]      = useState('uniform');
  const [whalePct,    setWhalePct]    = useState(0.10);
  const [smallLock,   setSmallLock]   = useState(224);
  const [data,        setData]        = useState<ConvictionData | null>(null);
  const [loading,     setLoading]     = useState(false);
  const [error,       setError]       = useState<string | null>(null);

  // Use proposals derived from ElectionContext candidates as "proposals"
  const proposalNames = config.candidates.map((c) => c.name);

  const runSimulation = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.post(`${API}${apiPath('election/conviction-voting')}`, {
        proposals:               config.candidates.map((c) => ({ name: c.name, x: c.x })),
        num_voters:              config.num_voters,
        ideology:                config.ideology,
        seed:                    config.seed,
        conviction_distribution: cvDist,
        whale_pct:               whalePct,
        small_lock_days:         smallLock,
      });
      setData(res.data);
    } catch {
      setError(t('conviction.error'));
    } finally {
      setLoading(false);
    }
  }, [config, cvDist, whalePct, smallLock, t]);

  const pNames = data?.proposals.map((p) => p.name) ?? proposalNames;

  return (
    <div>
      {/* Controls */}
      <Row className="g-2 mb-3 align-items-end">
        <Col xs={12} md={4}>
          <Form.Label className="small mb-0">{t('conviction.distribution')}</Form.Label>
          <Form.Select
            size="sm"
            value={cvDist}
            data-testid="distribution-select"
            onChange={(e) => setCvDist(e.target.value)}
          >
            <option value="uniform">{t('conviction.distUniform')}</option>
            <option value="skewed">{t('conviction.distSkewed')}</option>
            <option value="whale">{t('conviction.distWhale')}</option>
          </Form.Select>
        </Col>

        {cvDist === 'whale' && (
          <>
            <Col xs={12} md={3}>
              <Form.Label className="small mb-0">
                {t('conviction.whalePct')}: <strong>{Math.round(whalePct * 100)}%</strong>
              </Form.Label>
              <Form.Range
                data-testid="whale-pct-slider"
                min={0.05} max={0.5} step={0.05}
                value={whalePct}
                onChange={(e) => setWhalePct(Number(e.target.value))}
              />
            </Col>
            <Col xs={12} md={3}>
              <Form.Label className="small mb-0">{t('conviction.smallLock')}</Form.Label>
              <Form.Select
                size="sm"
                value={smallLock}
                data-testid="small-lock-select"
                onChange={(e) => setSmallLock(Number(e.target.value))}
              >
                {LOCK_OPTIONS.filter((d) => d > 0).map((d) => (
                  <option key={d} value={d}>{d} {t('conviction.days')} ×{MULTIPLIERS[d]}</option>
                ))}
              </Form.Select>
            </Col>
          </>
        )}

        <Col xs="auto">
          <Button variant="primary" onClick={runSimulation} disabled={loading}>
            {loading ? <Spinner size="sm" animation="border" /> : t('conviction.run')}
          </Button>
        </Col>
      </Row>

      {/* Conviction reference table */}
      <div className="mb-3" style={{ fontSize: '0.78rem' }}>
        <span className="text-muted">{t('conviction.lockRef')}: </span>
        {LOCK_OPTIONS.map((d) => (
          <Badge key={d} bg="light" text="dark" className="me-1">
            {d}j × {MULTIPLIERS[d]}
          </Badge>
        ))}
      </div>

      {!data && !loading && !error && (
        <Alert variant="info" role="alert">{t('conviction.prompt')}</Alert>
      )}
      {error && <Alert variant="danger">{error}</Alert>}

      {data && (
        <>
          {/* Winner comparison */}
          <div
            className={`d-flex align-items-center justify-content-around p-3 rounded mb-3 ${
              data.winner_changed ? 'border border-danger' : 'border border-success'
            }`}
            data-testid="comparison-banner"
          >
            <div className="text-center">
              <div className="text-muted" style={{ fontSize: '0.72rem' }}>{t('conviction.tokenWinner')}</div>
              <Badge
                style={{
                  background: propColor(data.token_winner, pNames),
                  fontSize: '0.85rem', padding: '6px 12px',
                }}
                data-testid="token-winner-badge"
              >
                {data.token_winner}
              </Badge>
            </div>
            <span style={{ fontSize: '1.4rem', color: data.winner_changed ? '#dc3545' : '#198754' }}>
              {data.winner_changed ? '⇒' : '='}
            </span>
            <div className="text-center">
              <div className="text-muted" style={{ fontSize: '0.72rem' }}>{t('conviction.cvWinner')}</div>
              <Badge
                style={{
                  background: propColor(data.conviction_winner, pNames),
                  fontSize: '0.85rem', padding: '6px 12px',
                }}
                data-testid="conviction-winner-badge"
              >
                {data.conviction_winner}
              </Badge>
            </div>
          </div>

          {data.winner_changed && (
            <Alert variant="danger" data-testid="winner-changed-alert">
              {t('conviction.winnerChanged')}
            </Alert>
          )}

          {/* Gini + whale dominance stats */}
          <div className="d-flex flex-wrap gap-2 mb-3">
            <Badge bg="secondary" data-testid="gini-tokens-badge">
              Gini tokens {data.voter_stats.gini_tokens.toFixed(3)}
            </Badge>
            <Badge
              bg={data.voter_stats.gini_conviction < data.voter_stats.gini_tokens ? 'success' : 'warning'}
              text={data.voter_stats.gini_conviction < data.voter_stats.gini_tokens ? undefined : 'dark'}
              data-testid="gini-conviction-badge"
            >
              Gini conviction {data.voter_stats.gini_conviction.toFixed(3)}
            </Badge>
            <Badge bg="info" text="dark" data-testid="whale-tokens-badge">
              {t('conviction.whaleDominance')} (tokens): {Math.round(data.voter_stats.whale_pct_tokens * 100)}%
            </Badge>
            <Badge bg="primary" data-testid="whale-conviction-badge">
              {t('conviction.whaleDominance')} (conviction): {Math.round(data.voter_stats.whale_pct_conviction * 100)}%
            </Badge>
          </div>

          {/* Scatter plot */}
          <div className="mb-3">
            <div className="fw-semibold mb-1" style={{ fontSize: '0.85rem' }}>
              {t('conviction.scatterTitle')}
            </div>
            <div className="border rounded" style={{ background: '#f8f9fa', overflow: 'hidden' }}>
              <ConvictionScatter
                dots={data.voter_scatter}
                proposalNames={pNames}
                t={t}
              />
            </div>
            <div className="d-flex gap-3 mt-1" style={{ fontSize: '0.72rem', color: '#6c757d' }}>
              {pNames.map((pn) => (
                <span key={pn}>
                  <span style={{
                    display: 'inline-block', width: 8, height: 8,
                    borderRadius: '50%', background: propColor(pn, pNames), marginRight: 3,
                  }} />
                  {pn}
                </span>
              ))}
              <span>{t('conviction.legendSize')}</span>
            </div>
          </div>

          {/* Comparison bars */}
          <div className="mb-3">
            <div className="fw-semibold mb-1" style={{ fontSize: '0.85rem' }}>
              {t('conviction.compareTitle')}
            </div>
            <CompareChart proposals={data.proposals} proposalNames={pNames} t={t} />
          </div>

          {/* Comparison table */}
          <Table size="sm" hover data-testid="proposals-table">
            <thead>
              <tr>
                <th style={{ fontSize: '0.78rem' }}>{t('conviction.proposal')}</th>
                <th style={{ fontSize: '0.78rem' }}>{t('conviction.cvScore')}</th>
                <th style={{ fontSize: '0.78rem' }}>{t('conviction.tokenScore')}</th>
                <th style={{ fontSize: '0.78rem' }}>Δ</th>
                <th style={{ fontSize: '0.78rem' }}>{t('conviction.avgMult')}</th>
              </tr>
            </thead>
            <tbody>
              {data.proposals.map((p) => {
                const delta = p.conviction_score - p.token_score;
                return (
                  <tr key={p.name}>
                    <td style={{ fontSize: '0.78rem' }}>
                      <span style={{
                        display: 'inline-block', width: 8, height: 8, borderRadius: '50%',
                        background: propColor(p.name, pNames), marginRight: 4,
                      }} />
                      {p.name}
                    </td>
                    <td style={{ fontSize: '0.78rem' }}>{Math.round(p.conviction_score).toLocaleString()}</td>
                    <td style={{ fontSize: '0.78rem' }}>{Math.round(p.token_score).toLocaleString()}</td>
                    <td style={{ fontSize: '0.78rem', color: delta >= 0 ? '#198754' : '#dc3545' }}>
                      {delta >= 0 ? '+' : ''}{Math.round(delta).toLocaleString()}
                    </td>
                    <td style={{ fontSize: '0.78rem' }}>×{p.avg_conviction_of_supporters.toFixed(2)}</td>
                  </tr>
                );
              })}
            </tbody>
          </Table>

          {/* Pedagogical note */}
          <Alert variant="secondary" style={{ fontSize: '0.8rem' }}>
            <strong>{t('conviction.noteTitle')}</strong> {data.pedagogical_note}
          </Alert>
        </>
      )}
    </div>
  );
};

export default ConvictionVotingPanel;
