/**
 * IntergenerationalPanel — democratic myopia & future-generation representation.
 * Rawls (1971) veil of ignorance applied to intergenerational justice.
 */
import React, { useState } from 'react';
import axios from 'axios';
import { useTranslation } from 'react-i18next';
import {
  Alert, Badge, Button, Col, Form, Row, Spinner, Table,
} from 'react-bootstrap';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, Cell,
} from 'recharts';

const API = process.env.REACT_APP_API_URL ?? 'http://localhost:4433';

// ── Types ─────────────────────────────────────────────────────────────────────

interface Decision {
  name:               string;
  cost_present:       number;
  benefit_future:     number;
  time_horizon_years: number;
}

interface MechResult {
  adopted:           boolean;
  vote_pct:          number;
  welfare_present:   number;
  welfare_future:    number;
  total_welfare_50y: number;
}

interface DecisionResult {
  decision_name: string;
  by_mechanism:  Record<string, MechResult>;
}

interface MechSummary {
  adoption_rate:          number;
  present_bias:           number;
  future_welfare_gain:    number;
  intergenerational_gini: number;
  avg_welfare_50y:        number;
}

interface IntergenerationalData {
  decisions_results:    DecisionResult[];
  mechanism_comparison: Record<string, MechSummary>;
  pedagogical_note:     string;
}

// ── Constants ─────────────────────────────────────────────────────────────────

const MECHANISMS = ['none', 'proxy', 'age_weighted', 'veto'] as const;
type Mechanism = typeof MECHANISMS[number];

const MECH_COLORS: Record<Mechanism, string> = {
  none:        '#dc3545',
  proxy:       '#fd7e14',
  age_weighted:'#0d6efd',
  veto:        '#198754',
};

const DEFAULT_DECISIONS: Decision[] = [
  { name: 'Retraite par répartition', cost_present: -0.2, benefit_future: -0.4, time_horizon_years: 30 },
  { name: 'Investissement éducation',  cost_present: -0.3, benefit_future:  0.8, time_horizon_years: 20 },
  { name: 'Dette publique',            cost_present:  0.5, benefit_future: -0.6, time_horizon_years: 25 },
  { name: 'Isolation des bâtiments',   cost_present: -0.4, benefit_future:  0.7, time_horizon_years: 15 },
  { name: 'Fonds souverain climatique',cost_present: -0.3, benefit_future:  0.9, time_horizon_years: 40 },
];

// ── Mini hemicycle SVG (adopted/rejected by mechanism) ────────────────────────

interface HemicycleProps {
  results: DecisionResult[];
  mechanism: Mechanism;
  color: string;
  label: string;
}

const MiniHemicycle: React.FC<HemicycleProps> = ({ results, mechanism, color, label }) => {
  const W = 160, H = 95, cx = W / 2, cy = H - 8, R = 70, r = 38;
  const n = results.length;
  if (n === 0) return null;

  const slices = results.map((dr, i) => {
    const sweep = Math.PI / n;
    const angle = Math.PI + i * sweep;
    const aEnd  = angle + sweep;
    const x1o = cx + R * Math.cos(angle), y1o = cy + R * Math.sin(angle);
    const x2o = cx + R * Math.cos(aEnd),  y2o = cy + R * Math.sin(aEnd);
    const x1i = cx + r * Math.cos(angle), y1i = cy + r * Math.sin(angle);
    const x2i = cx + r * Math.cos(aEnd),  y2i = cy + r * Math.sin(aEnd);
    const large = sweep > Math.PI ? 1 : 0;
    const d = `M${x1o} ${y1o} A${R} ${R} 0 ${large} 1 ${x2o} ${y2o} L${x2i} ${y2i} A${r} ${r} 0 ${large} 0 ${x1i} ${y1i}Z`;
    const adopted = dr.by_mechanism[mechanism]?.adopted ?? false;
    return (
      <path key={i} d={d} fill={adopted ? color : '#dee2e6'} stroke="#fff" strokeWidth={1}>
        <title>{dr.decision_name}: {adopted ? '✓ adopté' : '✗ rejeté'}</title>
      </path>
    );
  });

  const adopted = results.filter(dr => dr.by_mechanism[mechanism]?.adopted).length;

  return (
    <div style={{ textAlign: 'center' }}>
      <svg width={W} height={H} data-testid={`hemicycle-${mechanism}`}>{slices}</svg>
      <div style={{ fontSize: '0.7rem', fontWeight: 600, color }}>
        {label}
      </div>
      <div style={{ fontSize: '0.65rem', color: '#6c757d' }}>
        {adopted}/{n} {adopted === 1 ? 'décision' : 'décisions'}
      </div>
    </div>
  );
};

// ── Main panel ────────────────────────────────────────────────────────────────

const IntergenerationalPanel: React.FC = () => {
  const { t } = useTranslation();

  const [data,      setData]      = useState<IntergenerationalData | null>(null);
  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState<string | null>(null);
  const [decisions, setDecisions] = useState<Decision[]>(DEFAULT_DECISIONS);
  const [numVoters, setNumVoters] = useState(200);
  const [ageDist,   setAgeDist]   = useState([30, 45, 25]);   // %, must sum to 100
  const [seed,      setSeed]      = useState(42);
  const [activeView, setActiveView] = useState<'comparison' | 'welfare' | 'table'>('comparison');

  const updateDecision = (i: number, field: keyof Decision, val: string | number) =>
    setDecisions(prev => prev.map((d, j) => j === i ? { ...d, [field]: val } : d));

  const addDecision = () => setDecisions(prev => [
    ...prev,
    { name: `Décision ${prev.length + 1}`, cost_present: 0, benefit_future: 0.5, time_horizon_years: 20 },
  ]);

  const removeDecision = (i: number) =>
    setDecisions(prev => prev.filter((_, j) => j !== i));

  const normAgeDist = (): number[] => {
    const s = ageDist.reduce((a, b) => a + b, 0) || 100;
    return ageDist.map(x => x / s);
  };

  const handleRun = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.post(`${API}/api/theory/intergenerational`, {
        decisions,
        num_voters:                    numVoters,
        age_distribution:              normAgeDist(),
        seed,
        future_generations_mechanism:  'none',  // always compute all mechanisms
      });
      setData(res.data);
    } catch {
      setError(t('intergen.error'));
    } finally {
      setLoading(false);
    }
  };

  // ── Chart data ─────────────────────────────────────────────────────────────

  const comparisonChartData = data
    ? MECHANISMS.map(m => ({
        name:           t(`intergen.mech_${m}`),
        adoption:       Math.round((data.mechanism_comparison[m]?.adoption_rate ?? 0) * 100),
        welfare50y:     Math.round((data.mechanism_comparison[m]?.avg_welfare_50y ?? 0) * 100),
        futureGain:     Math.round((data.mechanism_comparison[m]?.future_welfare_gain ?? 0) * 100),
        gini:           Math.round((data.mechanism_comparison[m]?.intergenerational_gini ?? 0) * 100),
        color:          MECH_COLORS[m],
      }))
    : [];

  const welfareTimelineData = data
    ? data.decisions_results.map(dr => {
        const pt: Record<string, number | string> = { name: dr.decision_name.slice(0, 16) };
        MECHANISMS.forEach(m => {
          pt[`${m}_present`] = Math.round((dr.by_mechanism[m]?.welfare_present ?? 0) * 100);
          pt[`${m}_future`]  = Math.round((dr.by_mechanism[m]?.welfare_future  ?? 0) * 100);
        });
        return pt;
      })
    : [];

  const mechLabel = (m: Mechanism) => t(`intergen.mech_${m}`);

  return (
    <div>
      {/* ── Key message ── */}
      <Alert variant="info" className="py-2 mb-3" data-testid="key-message"
        style={{ fontSize: '0.78rem', borderLeft: '4px solid #0d6efd' }}>
        <strong>{t('intergen.keyMessageTitle')}</strong>{' '}
        {t('intergen.keyMessage')}
      </Alert>

      {/* ── Decision editor ── */}
      <div className="mb-3 border rounded p-2" style={{ background: '#f8f9fa' }}
        data-testid="decision-editor">
        <div className="fw-semibold mb-2" style={{ fontSize: '0.82rem' }}>
          {t('intergen.decisionsTitle')}
        </div>
        {decisions.map((d, i) => (
          <Row key={i} className="g-1 mb-1 align-items-center">
            <Col xs={12} md={3}>
              <Form.Control size="sm" value={d.name} placeholder={t('intergen.decisionName')}
                data-testid={`decision-name-${i}`}
                onChange={(e) => updateDecision(i, 'name', e.target.value)} />
            </Col>
            <Col xs={4} md={2}>
              <Form.Label className="small mb-0" style={{ fontSize: '0.65rem' }}>
                {t('intergen.costPresent')} {d.cost_present.toFixed(1)}
              </Form.Label>
              <Form.Range min={-10} max={10} step={1}
                value={Math.round(d.cost_present * 10)}
                data-testid={`decision-cost-${i}`}
                onChange={(e) => updateDecision(i, 'cost_present', Number(e.target.value) / 10)} />
            </Col>
            <Col xs={4} md={2}>
              <Form.Label className="small mb-0" style={{ fontSize: '0.65rem' }}>
                {t('intergen.benefitFuture')} {d.benefit_future.toFixed(1)}
              </Form.Label>
              <Form.Range min={-10} max={10} step={1}
                value={Math.round(d.benefit_future * 10)}
                data-testid={`decision-benefit-${i}`}
                onChange={(e) => updateDecision(i, 'benefit_future', Number(e.target.value) / 10)} />
            </Col>
            <Col xs={4} md={2}>
              <Form.Label className="small mb-0" style={{ fontSize: '0.65rem' }}>
                {t('intergen.horizon')} {d.time_horizon_years}y
              </Form.Label>
              <Form.Range min={1} max={50} step={1} value={d.time_horizon_years}
                data-testid={`decision-horizon-${i}`}
                onChange={(e) => updateDecision(i, 'time_horizon_years', Number(e.target.value))} />
            </Col>
            <Col xs="auto">
              <Button size="sm" variant="link" className="text-danger p-0"
                onClick={() => removeDecision(i)}>×</Button>
            </Col>
          </Row>
        ))}
        <Button size="sm" variant="outline-primary" className="mt-1"
          data-testid="add-decision-btn" onClick={addDecision}>
          + {t('intergen.addDecision')}
        </Button>
      </div>

      {/* ── Controls ── */}
      <Row className="g-2 mb-3 align-items-end">
        <Col xs={6} md={2}>
          <Form.Label className="small mb-0">{t('intergen.voters')}</Form.Label>
          <Form.Control type="number" size="sm" min={20} max={1000} value={numVoters}
            data-testid="voters-input"
            onChange={(e) => setNumVoters(Number(e.target.value))} />
        </Col>
        <Col xs={12} md={5}>
          <Form.Label className="small mb-0">
            {t('intergen.ageDist')} — {t('intergen.young')}: {ageDist[0]}% /
            {t('intergen.adult')}: {ageDist[1]}% / {t('intergen.senior')}: {ageDist[2]}%
          </Form.Label>
          <div className="d-flex gap-2">
            {[0, 1, 2].map(idx => (
              <Form.Range key={idx} min={5} max={70} step={5}
                value={ageDist[idx]}
                data-testid={`age-dist-${idx}`}
                onChange={(e) => setAgeDist(prev => {
                  const next = [...prev];
                  next[idx] = Number(e.target.value);
                  return next;
                })} />
            ))}
          </div>
        </Col>
        <Col xs={6} md={1}>
          <Form.Label className="small mb-0">{t('intergen.seed')}</Form.Label>
          <Form.Control type="number" size="sm" value={seed}
            data-testid="seed-input"
            onChange={(e) => setSeed(Number(e.target.value))} />
        </Col>
        <Col xs="auto">
          <Button variant="primary" size="sm" onClick={handleRun} disabled={loading}
            data-testid="run-btn">
            {loading ? <Spinner size="sm" animation="border" /> : t('intergen.run')}
          </Button>
        </Col>
      </Row>

      {!data && !loading && !error && (
        <Alert variant="secondary" data-testid="prompt-alert">{t('intergen.prompt')}</Alert>
      )}
      {error && <Alert variant="danger" data-testid="error-alert">{error}</Alert>}

      {data && (
        <>
          {/* ── 4 hemicycles ── */}
          <div className="mb-3" data-testid="hemicycles-section">
            <div className="fw-semibold mb-2" style={{ fontSize: '0.82rem' }}>
              {t('intergen.hemicyclesTitle')}
            </div>
            <Row className="g-2 justify-content-center">
              {MECHANISMS.map(m => (
                <Col key={m} xs={6} md={3} className="text-center">
                  <MiniHemicycle
                    results={data.decisions_results}
                    mechanism={m}
                    color={MECH_COLORS[m]}
                    label={mechLabel(m)}
                  />
                </Col>
              ))}
            </Row>
          </div>

          {/* ── View switcher ── */}
          <div className="d-flex gap-2 mb-3">
            {(['comparison', 'welfare', 'table'] as const).map(v => (
              <Button key={v} size="sm"
                variant={activeView === v ? 'dark' : 'outline-secondary'}
                data-testid={`view-btn-${v}`}
                onClick={() => setActiveView(v)}>
                {t(`intergen.view_${v}`)}
              </Button>
            ))}
          </div>

          {/* ── Comparison view (adoption + gini) ── */}
          {activeView === 'comparison' && (
            <div data-testid="comparison-view">
              <div className="fw-semibold mb-1" style={{ fontSize: '0.82rem' }}>
                {t('intergen.comparisonTitle')}
              </div>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={comparisonChartData}
                  margin={{ top: 5, right: 20, bottom: 20, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" tick={{ fontSize: 9 }} />
                  <YAxis tick={{ fontSize: 10 }} unit="%" domain={[0, 100]} />
                  <Tooltip formatter={(v: number) => `${v}%`} />
                  <Legend wrapperStyle={{ fontSize: '0.7rem' }} />
                  <Bar dataKey="adoption" name={t('intergen.adoptionRate')} radius={[3, 3, 0, 0]}>
                    {comparisonChartData.map((pt, i) => (
                      <Cell key={i} fill={pt.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              <div className="text-muted mt-1" style={{ fontSize: '0.7rem' }}>
                {t('intergen.comparisonDesc')}
              </div>
            </div>
          )}

          {/* ── Welfare timeline view ── */}
          {activeView === 'welfare' && (
            <div data-testid="welfare-view">
              <div className="fw-semibold mb-1" style={{ fontSize: '0.82rem' }}>
                {t('intergen.welfareTitle')}
              </div>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={welfareTimelineData}
                  margin={{ top: 5, right: 20, bottom: 40, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" tick={{ fontSize: 8 }} angle={-30} textAnchor="end" />
                  <YAxis tick={{ fontSize: 10 }} unit="%" domain={[0, 100]} />
                  <Tooltip formatter={(v: number) => `${v}%`} />
                  <Legend wrapperStyle={{ fontSize: '0.7rem' }} />
                  <Bar dataKey="none_future"        name={`${mechLabel('none')} — futur`}        fill={MECH_COLORS.none}        opacity={0.6} stackId="a" />
                  <Bar dataKey="veto_future"        name={`${mechLabel('veto')} — futur`}        fill={MECH_COLORS.veto}        opacity={0.9} stackId="b" />
                  <Bar dataKey="age_weighted_future" name={`${mechLabel('age_weighted')} — futur`} fill={MECH_COLORS.age_weighted} opacity={0.9} stackId="c" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* ── Table view ── */}
          {activeView === 'table' && (
            <div data-testid="table-view" style={{ overflowX: 'auto' }}>
              <Table size="sm" bordered style={{ fontSize: '0.73rem' }}>
                <thead className="table-light">
                  <tr>
                    <th>{t('intergen.colMechanism')}</th>
                    <th>{t('intergen.colAdoption')}</th>
                    <th>{t('intergen.colPresentBias')}</th>
                    <th>{t('intergen.colFutureGain')}</th>
                    <th>{t('intergen.colGini')}</th>
                    <th>{t('intergen.colWelfare50y')}</th>
                  </tr>
                </thead>
                <tbody>
                  {MECHANISMS.map(m => {
                    const s = data.mechanism_comparison[m];
                    const isBest = m === Object.keys(data.mechanism_comparison).reduce(
                      (best, k) => data.mechanism_comparison[k].avg_welfare_50y > data.mechanism_comparison[best].avg_welfare_50y ? k : best,
                      'none'
                    );
                    return (
                      <tr key={m} style={{ background: isBest ? '#d1e7dd' : undefined }}
                        data-testid={`table-row-${m}`}>
                        <td>
                          <Badge style={{ background: MECH_COLORS[m], fontSize: '0.65rem' }}>
                            {mechLabel(m)}
                          </Badge>
                        </td>
                        <td>{Math.round(s.adoption_rate * 100)}%</td>
                        <td>
                          <span style={{ color: s.present_bias > 0.3 ? '#dc3545' : '#198754' }}>
                            {Math.round(s.present_bias * 100)}%
                          </span>
                        </td>
                        <td>
                          <span style={{ color: s.future_welfare_gain >= 0 ? '#198754' : '#dc3545' }}>
                            {s.future_welfare_gain >= 0 ? '+' : ''}{Math.round(s.future_welfare_gain * 100)}%
                          </span>
                        </td>
                        <td>{Math.round(s.intergenerational_gini * 100)}%</td>
                        <td style={{ fontWeight: 700 }}>{Math.round(s.avg_welfare_50y * 100)}%</td>
                      </tr>
                    );
                  })}
                </tbody>
              </Table>
            </div>
          )}

          {/* ── Per-decision breakdown ── */}
          <div className="mt-3" data-testid="decisions-breakdown">
            <div className="fw-semibold mb-1" style={{ fontSize: '0.82rem' }}>
              {t('intergen.breakdownTitle')}
            </div>
            <div className="d-flex flex-wrap gap-2">
              {data.decisions_results.map((dr, i) => (
                <div key={i} className="border rounded p-2"
                  style={{ background: '#fff', fontSize: '0.7rem', minWidth: 120 }}
                  data-testid={`decision-result-${i}`}>
                  <div className="fw-semibold mb-1" style={{ fontSize: '0.72rem' }}>
                    {dr.decision_name}
                  </div>
                  {MECHANISMS.map(m => {
                    const r = dr.by_mechanism[m];
                    return (
                      <div key={m} style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 2 }}>
                        <span style={{ width: 8, height: 8, borderRadius: '50%',
                          background: MECH_COLORS[m], display: 'inline-block' }} />
                        <span style={{ color: r.adopted ? '#198754' : '#dc3545' }}>
                          {r.adopted ? '✓' : '✗'}
                        </span>
                        <span style={{ color: '#6c757d' }}>{Math.round(r.vote_pct * 100)}%</span>
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>

          {/* ── Real-world examples ── */}
          <div className="mt-3 border rounded p-3" data-testid="examples-section"
            style={{ background: '#f8f9fa', fontSize: '0.75rem' }}>
            <div className="fw-semibold mb-2">{t('intergen.examplesTitle')}</div>
            <Row className="g-2">
              {([
                { flag: '🏴󠁧󠁢󠁷󠁬󠁳󠁿', place: 'Pays de Galles', desc: 'Future Generations Commissioner (2015) — droit de regard sur toute loi affectant l\'avenir.' },
                { flag: '🇫🇮', place: 'Finlande',       desc: 'Committee for the Future (1993) — comité parlementaire permanent sur les décisions à long terme.' },
                { flag: '🇭🇺', place: 'Hongrie',        desc: 'Ombudsman pour les générations futures (2007) — supprimé en 2012 sous Orbán.' },
                { flag: '🌍', place: 'ONU',              desc: 'Proposition "Déclaration des générations futures" — actuellement en discussion.' },
              ] as const).map(({ flag, place, desc }) => (
                <Col key={place} xs={12} md={6}>
                  <div className="border rounded p-2" style={{ background: '#fff' }}>
                    <strong>{flag} {place}</strong>
                    <div className="text-muted" style={{ fontSize: '0.7rem' }}>{desc}</div>
                  </div>
                </Col>
              ))}
            </Row>
          </div>

          {/* ── Pedagogical note ── */}
          <Alert variant="secondary" className="mt-3" style={{ fontSize: '0.8rem' }}
            data-testid="pedagogical-note">
            <strong>{t('intergen.noteTitle')}</strong> {data.pedagogical_note}
          </Alert>
        </>
      )}
    </div>
  );
};

export default IntergenerationalPanel;
