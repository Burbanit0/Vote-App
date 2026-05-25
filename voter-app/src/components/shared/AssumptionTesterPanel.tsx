/**
 * AssumptionTesterPanel — interactive model assumption stress-tester.
 * Shows how results change when core spatial-model assumptions are violated.
 */
import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useTranslation } from 'react-i18next';
import {
  Alert, Badge, Button, Col, Form, Row, Spinner,
} from 'react-bootstrap';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from 'recharts';
import { apiPath } from '../../api/apiVersion';

const API = process.env.REACT_APP_API_URL ?? 'http://localhost:4433';

// ── Types ─────────────────────────────────────────────────────────────────────

interface RelaxedResult {
  winner:              string;
  winner_changed:      boolean;
  pct_trials_changed:  number;
  result_variance:     number;
  confidence_interval: [number, number];
  winner_distribution: Record<string, number>;
}

interface AssumptionData {
  baseline_result:          { winner: string; regret: number };
  relaxed_results:          Record<string, RelaxedResult>;
  most_fragile_assumption:  string;
  robust_result:            boolean;
  pedagogical_note:         string;
}

// ── Constants ─────────────────────────────────────────────────────────────────

const ALL_ASSUMPTIONS = [
  'single_peaked',
  'stable_preferences',
  'rational_voters',
  'fixed_electorate',
  'measurable_utilities',
] as const;
type Assumption = typeof ALL_ASSUMPTIONS[number];

const ASSUMPTION_COLORS: Record<Assumption, string> = {
  single_peaked:        '#dc3545',
  stable_preferences:   '#fd7e14',
  rational_voters:      '#ffc107',
  fixed_electorate:     '#0d6efd',
  measurable_utilities: '#6f42c1',
};

const VARIANCE_THRESHOLDS = { low: 0.15, medium: 0.40 };

function variantFor(v: number): string {
  if (v < VARIANCE_THRESHOLDS.low)    return 'success';
  if (v < VARIANCE_THRESHOLDS.medium) return 'warning';
  return 'danger';
}

// ── Fragility indicator bar ───────────────────────────────────────────────────

const FragilityBar: React.FC<{ value: number; label: string }> = ({ value, label }) => {
  const pct    = Math.round(value * 100);
  const color  = pct < 15 ? '#198754' : pct < 40 ? '#ffc107' : '#dc3545';
  return (
    <div style={{ marginBottom: 6 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', marginBottom: 2 }}>
        <span>{label}</span>
        <span style={{ color, fontWeight: 700 }}>{pct}%</span>
      </div>
      <div style={{ height: 6, background: '#dee2e6', borderRadius: 3, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, transition: 'width 0.4s' }} />
      </div>
    </div>
  );
};

// ── Philosophy quote ──────────────────────────────────────────────────────────

const PhilosophyQuote: React.FC = () => {
  const { t } = useTranslation();
  return (
    <div data-testid="philosophy-quote"
      style={{
        borderLeft: '4px solid #6c757d', paddingLeft: 12,
        fontSize: '0.78rem', color: '#495057', fontStyle: 'italic',
      }}>
      <strong style={{ fontStyle: 'normal' }}>{t('assumptions.philoTitle')}</strong>
      <p className="mt-1 mb-0">{t('assumptions.philoText')}</p>
    </div>
  );
};

// ── Assumption detail card ────────────────────────────────────────────────────

interface AssumptionCardProps {
  id:       Assumption;
  checked:  boolean;
  onToggle: () => void;
  result?:  RelaxedResult;
  isMostFragile: boolean;
  t: (k: string) => string;
}

const AssumptionCard: React.FC<AssumptionCardProps> = ({
  id, checked, onToggle, result, isMostFragile, t,
}) => {
  const [expanded, setExpanded] = useState(false);
  return (
    <div
      className="border rounded p-2 mb-2"
      style={{
        background: isMostFragile ? '#fff3cd' : '#fff',
        borderColor: isMostFragile ? '#ffc107' : undefined,
        fontSize: '0.78rem',
      }}
      data-testid={`assumption-card-${id}`}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
        <Form.Check type="checkbox" id={`assumption-${id}`}
          checked={checked}
          data-testid={`assumption-cb-${id}`}
          onChange={onToggle}
          style={{ marginTop: 2 }} />
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
            <span className="fw-semibold">{t(`assumptions.name_${id}`)}</span>
            {isMostFragile && (
              <Badge bg="warning" text="dark" style={{ fontSize: '0.6rem' }}>
                {t('assumptions.mostFragile')}
              </Badge>
            )}
            {result && (
              <Badge bg={variantFor(result.result_variance)} style={{ fontSize: '0.6rem' }}>
                {t('assumptions.variance')}: {Math.round(result.result_variance * 100)}%
              </Badge>
            )}
          </div>
          <div className="text-muted" style={{ fontSize: '0.7rem', marginTop: 2 }}>
            {t(`assumptions.desc_${id}`)}
          </div>

          {result && (
            <div className="mt-1">
              {result.winner_changed ? (
                <span style={{ color: '#dc3545', fontSize: '0.7rem', fontWeight: 700 }}>
                  ⚡ {t('assumptions.winnerChanged')}: {result.winner}
                  {' '}({Math.round(result.pct_trials_changed * 100)}% {t('assumptions.ofTrials')})
                </span>
              ) : (
                <span style={{ color: '#198754', fontSize: '0.7rem' }}>
                  ✓ {t('assumptions.winnerStable')}: {result.winner}
                  {' '}[{Math.round(result.confidence_interval[0] * 100)}–{Math.round(result.confidence_interval[1] * 100)}%]
                </span>
              )}
              <Button variant="link" size="sm"
                style={{ fontSize: '0.65rem', padding: '0 4px' }}
                onClick={() => setExpanded(e => !e)}>
                {expanded ? '▲' : '▼'} {t('assumptions.distribution')}
              </Button>
              {expanded && (
                <div style={{ marginTop: 4 }}>
                  {Object.entries(result.winner_distribution).map(([cand, pct]) => (
                    <div key={cand} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <span style={{ width: 40, fontSize: '0.68rem' }}>{cand}</span>
                      <div style={{ flex: 1, height: 8, background: '#dee2e6', borderRadius: 3 }}>
                        <div style={{
                          width: `${Math.round(pct * 100)}%`, height: '100%',
                          background: ASSUMPTION_COLORS[id] ?? '#0d6efd', borderRadius: 3,
                        }} />
                      </div>
                      <span style={{ fontSize: '0.68rem', width: 32 }}>
                        {Math.round(pct * 100)}%
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// ── Lab-mode props ────────────────────────────────────────────────────────────

export interface AssumptionTesterLabProps {
  labMode?:        boolean;
  labCandidates?:  Array<{name: string; x: number; y: number}>;
  labNumVoters?:   number;
  labSeed?:        number;
  labIdeology?:    string;
}

// ── Main panel ────────────────────────────────────────────────────────────────

const AssumptionTesterPanel: React.FC<AssumptionTesterLabProps> = ({
  labMode = false, labCandidates, labNumVoters, labSeed, labIdeology,
}) => {
  const { t } = useTranslation();

  const [data,       setData]       = useState<AssumptionData | null>(null);
  const [loading,    setLoading]    = useState(false);
  const [error,      setError]      = useState<string | null>(null);
  const [selected,   setSelected]   = useState<Set<Assumption>>(new Set(ALL_ASSUMPTIONS));
  const [numVoters,  setNumVoters]  = useState(100);
  const [seed,       setSeed]       = useState(42);

  const toggle = (a: Assumption) =>
    setSelected(prev => {
      const next = new Set(prev);
      next.has(a) ? next.delete(a) : next.add(a);
      return next;
    });

  const DEFAULT_CANDS = [
    { name: 'Alice', x: -0.4, y: 0.0 },
    { name: 'Bob',   x:  0.1, y: 0.0 },
    { name: 'Carol', x:  0.5, y: 0.0 },
  ];

  const handleRun = async (
    overrideCands?: typeof DEFAULT_CANDS,
    overrideVoters?: number,
    overrideSeed?: number,
    overrideIdeology?: string,
  ) => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.post(`${API}${apiPath('theory/assumption-testing')}`, {
        base_simulation: {
          candidates:  overrideCands   ?? DEFAULT_CANDS,
          num_voters:  overrideVoters  ?? numVoters,
          ideology:    overrideIdeology ?? 'random',
          seed:        overrideSeed    ?? seed,
        },
        assumptions_to_relax: [...selected],
      });
      setData(res.data);
    } catch {
      setError(t('assumptions.error'));
    } finally {
      setLoading(false);
    }
  };

  // Auto-run when lab context changes
  useEffect(() => {
    if (labMode && labCandidates?.length) {
      handleRun(labCandidates, labNumVoters, labSeed, labIdeology);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [labMode, labCandidates, labNumVoters, labSeed, labIdeology]);

  // ── Fragility radar data ─────────────────────────────────────────────────
  const fragilityData = data
    ? [...selected].map(a => ({
        name:      t(`assumptions.short_${a}`),
        variance:  Math.round((data.relaxed_results[a]?.result_variance ?? 0) * 100),
        changed:   data.relaxed_results[a]?.winner_changed ? 1 : 0,
        color:     ASSUMPTION_COLORS[a],
      }))
    : [];

  return (
    <div>
      {/* ── Philosophy quote (always visible) ── */}
      <PhilosophyQuote />

      {/* ── Lab mode badge ── */}
      {labMode && (
        <div className="mt-2 mb-1">
          <Badge bg="dark" style={{ fontSize: '0.68rem' }}>
            🔬 {t('lab.fromElectionLab')}
          </Badge>
        </div>
      )}

      {/* ── Controls (hidden in lab mode for election config) ── */}
      {!labMode && (
      <Row className="g-2 my-3 align-items-end">
        <Col xs={6} md={2}>
          <Form.Label className="small mb-0">{t('assumptions.voters')}</Form.Label>
          <Form.Control type="number" size="sm" min={20} max={500} value={numVoters}
            data-testid="voters-input"
            onChange={(e) => setNumVoters(Number(e.target.value))} />
        </Col>
        <Col xs={6} md={1}>
          <Form.Label className="small mb-0">{t('assumptions.seed')}</Form.Label>
          <Form.Control type="number" size="sm" value={seed}
            data-testid="seed-input"
            onChange={(e) => setSeed(Number(e.target.value))} />
        </Col>
        <Col xs="auto">
          <Button variant="secondary" size="sm" onClick={() => handleRun()} disabled={loading || selected.size === 0}
            data-testid="run-btn">
            {loading ? <Spinner size="sm" animation="border" /> : t('assumptions.run')}
          </Button>
        </Col>
        <Col xs="auto" className="ms-auto">
          <Button size="sm" variant="link" className="text-muted p-0"
            onClick={() => setSelected(new Set(ALL_ASSUMPTIONS))}>
            {t('assumptions.selectAll')}
          </Button>
          {' · '}
          <Button size="sm" variant="link" className="text-muted p-0"
            onClick={() => setSelected(new Set())}>
            {t('assumptions.selectNone')}
          </Button>
        </Col>
      </Row>
      )}

      {!data && !loading && !error && !labMode && (
        <Alert variant="secondary" data-testid="prompt-alert">{t('assumptions.prompt')}</Alert>
      )}
      {error && <Alert variant="danger" data-testid="error-alert">{error}</Alert>}

      {/* ── Assumption cards ── */}
      <div data-testid="assumption-cards">
        {ALL_ASSUMPTIONS.map(a => (
          <AssumptionCard key={a} id={a}
            checked={selected.has(a)}
            onToggle={() => toggle(a)}
            result={data?.relaxed_results[a]}
            isMostFragile={data?.most_fragile_assumption === a}
            t={t} />
        ))}
      </div>

      {data && (
        <>
          {/* ── Baseline + summary ── */}
          <div className="mt-3 border rounded p-3" data-testid="summary-section"
            style={{ background: '#f8f9fa', fontSize: '0.78rem' }}>
            <div className="d-flex gap-3 flex-wrap align-items-center">
              <div>
                <span className="text-muted">{t('assumptions.baselineWinner')}:</span>
                {' '}<Badge bg="primary">{data.baseline_result.winner}</Badge>
              </div>
              <Badge bg={data.robust_result ? 'success' : 'danger'}
                data-testid="robust-badge">
                {data.robust_result ? t('assumptions.robust') : t('assumptions.fragile')}
              </Badge>
              {data.most_fragile_assumption && (
                <span>
                  <span className="text-muted">{t('assumptions.mostFragileLabel')}:</span>
                  {' '}<Badge bg="warning" text="dark">
                    {t(`assumptions.short_${data.most_fragile_assumption}`)}
                  </Badge>
                </span>
              )}
            </div>
          </div>

          {/* ── Fragility bar chart ── */}
          {fragilityData.length > 0 && (
            <div className="mt-3" data-testid="fragility-chart">
              <div className="fw-semibold mb-2" style={{ fontSize: '0.82rem' }}>
                {t('assumptions.fragilityTitle')}
              </div>
              {fragilityData.map(d => (
                <FragilityBar key={d.name} value={d.variance / 100} label={d.name} />
              ))}
            </div>
          )}

          {/* ── Variance bar chart ── */}
          <div className="mt-3" data-testid="variance-chart">
            <div className="fw-semibold mb-1" style={{ fontSize: '0.82rem' }}>
              {t('assumptions.varianceTitle')}
            </div>
            <ResponsiveContainer width="100%" height={160}>
              <BarChart data={fragilityData}
                margin={{ top: 5, right: 20, bottom: 30, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fontSize: 8 }} angle={-20} textAnchor="end" />
                <YAxis tick={{ fontSize: 10 }} unit="%" domain={[0, 100]} />
                <Tooltip formatter={(v: number) => `${v}%`}
                  labelFormatter={(l) => `${l}`} />
                <Bar dataKey="variance" name={t('assumptions.varianceLabel')} radius={[3, 3, 0, 0]}>
                  {fragilityData.map((d, i) => <Cell key={i} fill={d.color} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <div className="text-muted mt-1" style={{ fontSize: '0.7rem' }}>
              {t('assumptions.varianceDesc')}
            </div>
          </div>

          {/* ── Real assumption reference table ── */}
          <div className="mt-3 border rounded p-3" data-testid="reference-section"
            style={{ background: '#f8f9fa', fontSize: '0.74rem' }}>
            <div className="fw-semibold mb-2">{t('assumptions.referenceTitle')}</div>
            <table className="table table-sm" style={{ fontSize: '0.72rem' }}>
              <thead className="table-light">
                <tr>
                  <th>{t('assumptions.refColAssumption')}</th>
                  <th>{t('assumptions.refColViolation')}</th>
                  <th>{t('assumptions.refColRef')}</th>
                </tr>
              </thead>
              <tbody>
                {ALL_ASSUMPTIONS.map(a => (
                  <tr key={a}>
                    <td>{t(`assumptions.name_${a}`)}</td>
                    <td className="text-muted">{t(`assumptions.violation_${a}`)}</td>
                    <td style={{ fontStyle: 'italic' }}>{t(`assumptions.ref_${a}`)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* ── Pedagogical note ── */}
          <Alert variant="secondary" className="mt-3" style={{ fontSize: '0.8rem' }}
            data-testid="pedagogical-note">
            <strong>{t('assumptions.noteTitle')}</strong> {data.pedagogical_note}
          </Alert>
        </>
      )}
    </div>
  );
};

export default AssumptionTesterPanel;
