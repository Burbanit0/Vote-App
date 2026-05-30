/**
 * MajorityTyrannyPanel — Tocqueville (1835) tyranny of the majority.
 * Shows how decision rules protect (or fail to protect) permanent minorities.
 */
import React, { useCallback, useState } from 'react';
import { $api } from '../../api/hooks';
import { useTranslation } from 'react-i18next';
import {
  Alert, Badge, Button, Col, Form, Row, Spinner,
} from 'react-bootstrap';
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer,
} from 'recharts';


const ALL_RULES = [
  'simple_majority', 'supermajority_2_3', 'supermajority_3_4',
  'unanimous', 'qv', 'mj',
] as const;
type Rule = typeof ALL_RULES[number];

// ── Types ─────────────────────────────────────────────────────────────────────

interface RuleResult {
  minority_win_rate:     number;
  minority_satisfaction: number;
  majority_satisfaction: number;
  total_welfare:         number;
  efficiency_loss:       number;
  tyranny_index:         number;
}

interface TyrannyData {
  results:          Record<Rule, RuleResult>;
  tyranny_curve:    { majority_pct: number; tyranny_by_rule: Record<Rule, number> }[];
  best_protector:   string;
  least_efficient:  string;
  pedagogical_note: string;
}

// ── Rule display helpers ───────────────────────────────────────────────────────

const RULE_COLORS: Record<string, string> = {
  simple_majority:    '#dc3545',
  supermajority_2_3:  '#fd7e14',
  supermajority_3_4:  '#ffc107',
  unanimous:          '#198754',
  qv:                 '#0d6efd',
  mj:                 '#6f42c1',
};

// ── Radar data builder ────────────────────────────────────────────────────────

function buildRadarData(results: Record<string, RuleResult>): object[] {
  const axes = [
    { key: 'minority_protection', fn: (r: RuleResult) => r.minority_win_rate },
    { key: 'efficiency',          fn: (r: RuleResult) => 1 - r.efficiency_loss },
    { key: 'majority_satisfaction', fn: (r: RuleResult) => r.majority_satisfaction },
    { key: 'welfare',             fn: (r: RuleResult) => r.total_welfare },
    { key: 'balance',             fn: (r: RuleResult) => 1 - r.tyranny_index },
  ];
  return axes.map(({ key, fn }) => {
    const point: Record<string, number | string> = { axis: key };
    for (const [rule, res] of Object.entries(results)) {
      point[rule] = Math.round(fn(res) * 100);
    }
    return point;
  });
}

// ── Main panel ────────────────────────────────────────────────────────────────

const MajorityTyrannyPanel: React.FC = () => {
  const { t } = useTranslation();

  const sim = $api.useMutation('post', '/api/v2/theory/majority-tyranny');
  const data: TyrannyData | null = (sim.data as TyrannyData | undefined) ?? null;
  const loading = sim.isPending;
  const error = sim.isError ? t('tyranny.error') : null;
  const [numVoters, setNumVoters] = useState(100);
  const [majorityPct, setMajorityPct] = useState(0.60);
  const [intensity, setIntensity] = useState(3.0);
  const [numDecisions, setNumDecisions] = useState(50);
  const [seed,      setSeed]      = useState(42);
  const [rules,     setRules]     = useState<Rule[]>([...ALL_RULES]);
  const [activeView, setActiveView] = useState<'radar' | 'curve' | 'table'>('radar');

  const toggleRule = (r: Rule) =>
    setRules((prev) =>
      prev.includes(r) ? (prev.length > 1 ? prev.filter((x) => x !== r) : prev) : [...prev, r]
    );

  const run = useCallback(() => {
    sim.mutate({ body: {
      num_voters:       numVoters,
      majority_pct:     majorityPct,
      minority_intensity: intensity,
      num_decisions:    numDecisions,
      seed,
      decision_rules:   rules,
    } });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [numVoters, majorityPct, intensity, numDecisions, seed, rules, sim]);

  const nMin = Math.round(numVoters * (1 - majorityPct));
  const nMaj = numVoters - nMin;

  return (
    <div>
      {/* ── Provocative quote ── */}
      <Alert variant="danger" className="py-2 mb-3" data-testid="tocqueville-quote"
        style={{ fontSize: '0.78rem', borderLeft: '4px solid #dc3545' }}>
        <strong>{t('tyranny.hitlerQuoteTitle')}</strong>{' '}
        {t('tyranny.hitlerQuote')}
      </Alert>

      {/* ── Controls ── */}
      <Row className="g-2 mb-3 align-items-end">
        <Col xs={6} md={2}>
          <Form.Label className="small mb-0">{t('tyranny.voters')}</Form.Label>
          <Form.Control type="number" size="sm" min={20} max={500} value={numVoters}
            data-testid="voters-input"
            onChange={(e) => setNumVoters(Number(e.target.value))} />
        </Col>
        <Col xs={6} md={3}>
          <Form.Label className="small mb-0">
            {t('tyranny.majoritySize')} — {Math.round(majorityPct * 100)}%
            <span className="text-muted ms-1" style={{ fontSize: '0.7rem' }}>
              ({nMaj} {t('tyranny.maj')} / {nMin} {t('tyranny.min')})
            </span>
          </Form.Label>
          <Form.Range min={51} max={80} value={Math.round(majorityPct * 100)}
            data-testid="majority-slider"
            onChange={(e) => setMajorityPct(Number(e.target.value) / 100)} />
        </Col>
        <Col xs={6} md={3}>
          <Form.Label className="small mb-0">
            {t('tyranny.intensity')} — ×{intensity.toFixed(1)}
          </Form.Label>
          <Form.Range min={1} max={10} step={0.5} value={intensity}
            data-testid="intensity-slider"
            onChange={(e) => setIntensity(Number(e.target.value))} />
        </Col>
        <Col xs={6} md={2}>
          <Form.Label className="small mb-0">{t('tyranny.decisions')}</Form.Label>
          <Form.Control type="number" size="sm" min={10} max={200} value={numDecisions}
            data-testid="decisions-input"
            onChange={(e) => setNumDecisions(Number(e.target.value))} />
        </Col>
        <Col xs={6} md={1}>
          <Form.Label className="small mb-0">{t('tyranny.seed')}</Form.Label>
          <Form.Control type="number" size="sm" value={seed}
            data-testid="seed-input"
            onChange={(e) => setSeed(Number(e.target.value))} />
        </Col>
        <Col xs="auto">
          <Button variant="danger" onClick={run} disabled={loading}
            data-testid="run-btn">
            {loading ? <Spinner size="sm" animation="border" /> : t('tyranny.run')}
          </Button>
        </Col>
      </Row>

      {/* ── Rule toggles ── */}
      <div className="d-flex flex-wrap gap-2 mb-3" data-testid="rule-toggles">
        {ALL_RULES.map((r) => (
          <Badge key={r}
            bg={rules.includes(r) ? undefined : 'light'}
            text={rules.includes(r) ? undefined : 'dark'}
            style={{
              cursor: 'pointer', fontSize: '0.72rem', padding: '6px 10px',
              background: rules.includes(r) ? RULE_COLORS[r] : undefined,
            }}
            onClick={() => toggleRule(r)}
            data-testid={`rule-badge-${r}`}>
            {t(`tyranny.rule_${r}`)}
          </Badge>
        ))}
      </div>

      {!data && !loading && !error && (
        <Alert variant="secondary" data-testid="prompt-alert">{t('tyranny.prompt')}</Alert>
      )}
      {error && <Alert variant="danger" data-testid="error-alert">{error}</Alert>}

      {data && (
        <>
          {/* ── Summary badges ── */}
          <div className="d-flex flex-wrap gap-2 mb-3" data-testid="summary-badges">
            <Badge bg="success" data-testid="best-protector-badge">
              🛡 {t('tyranny.bestProtector')}: {t(`tyranny.rule_${data.best_protector}`)}
            </Badge>
            <Badge bg="warning" text="dark" data-testid="least-efficient-badge">
              ⚠ {t('tyranny.leastEfficient')}: {t(`tyranny.rule_${data.least_efficient}`)}
            </Badge>
          </div>

          {/* ── View switcher ── */}
          <div className="d-flex gap-2 mb-3">
            {(['radar', 'curve', 'table'] as const).map((v) => (
              <Button key={v} size="sm"
                variant={activeView === v ? 'dark' : 'outline-secondary'}
                data-testid={`view-btn-${v}`}
                onClick={() => setActiveView(v)}>
                {t(`tyranny.view_${v}`)}
              </Button>
            ))}
          </div>

          {/* ── Radar view ── */}
          {activeView === 'radar' && (
            <div data-testid="radar-view">
              <div className="fw-semibold mb-1" style={{ fontSize: '0.85rem' }}>
                {t('tyranny.radarTitle')}
              </div>
              <ResponsiveContainer width="100%" height={320}>
                <RadarChart data={buildRadarData(data.results)}
                  margin={{ top: 10, right: 20, bottom: 10, left: 20 }}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="axis"
                    tickFormatter={(v: string) => t(`tyranny.axis_${v}`)}
                    tick={{ fontSize: 10 }} />
                  {rules.map((r) => (
                    <Radar key={r} name={t(`tyranny.rule_${r}`)} dataKey={r}
                      stroke={RULE_COLORS[r]} fill={RULE_COLORS[r]} fillOpacity={0.12} />
                  ))}
                  <Legend iconSize={10} wrapperStyle={{ fontSize: '0.72rem' }} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* ── Tyranny curve view ── */}
          {activeView === 'curve' && (
            <div data-testid="curve-view">
              <div className="fw-semibold mb-1" style={{ fontSize: '0.85rem' }}>
                {t('tyranny.curveTitle')}
              </div>
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={data.tyranny_curve.map((pt) => ({
                  pct: Math.round(pt.majority_pct * 100),
                  ...pt.tyranny_by_rule,
                }))} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="pct" unit="%" tick={{ fontSize: 10 }} />
                  <YAxis domain={[0, 1]} tickFormatter={(v) => `${Math.round(v * 100)}%`}
                    tick={{ fontSize: 10 }} />
                  <Tooltip formatter={(v: number) => `${Math.round(v * 100)}%`} />
                  <Legend iconSize={10} wrapperStyle={{ fontSize: '0.72rem' }} />
                  {rules.map((r) => (
                    <Line key={r} type="monotone" dataKey={r}
                      name={t(`tyranny.rule_${r}`)}
                      stroke={RULE_COLORS[r]} strokeWidth={2} dot={false} />
                  ))}
                </LineChart>
              </ResponsiveContainer>
              <div className="text-muted mt-1" style={{ fontSize: '0.7rem' }}>
                {t('tyranny.curveDesc')}
              </div>
            </div>
          )}

          {/* ── Table view ── */}
          {activeView === 'table' && (
            <div data-testid="table-view" style={{ overflowX: 'auto' }}>
              <table className="table table-sm table-bordered"
                style={{ fontSize: '0.76rem' }}>
                <thead className="table-light">
                  <tr>
                    <th>{t('tyranny.colRule')}</th>
                    <th>{t('tyranny.colMinWin')}</th>
                    <th>{t('tyranny.colMinSat')}</th>
                    <th>{t('tyranny.colMajSat')}</th>
                    <th>{t('tyranny.colWelfare')}</th>
                    <th>{t('tyranny.colEffLoss')}</th>
                    <th>{t('tyranny.colTyranny')}</th>
                  </tr>
                </thead>
                <tbody>
                  {rules.filter((r) => data.results[r]).map((r) => {
                    const res = data.results[r];
                    const isBest = r === data.best_protector;
                    return (
                      <tr key={r} style={{ background: isBest ? '#d1e7dd' : undefined }}
                        data-testid={`row-${r}`}>
                        <td>
                          <span className="badge" style={{
                            background: RULE_COLORS[r], fontSize: '0.68rem',
                          }}>
                            {t(`tyranny.rule_${r}`)}
                          </span>
                        </td>
                        <td>{Math.round(res.minority_win_rate * 100)}%</td>
                        <td>{Math.round(res.minority_satisfaction * 100)}%</td>
                        <td>{Math.round(res.majority_satisfaction * 100)}%</td>
                        <td>{res.total_welfare.toFixed(2)}</td>
                        <td>{Math.round(res.efficiency_loss * 100)}%</td>
                        <td>
                          <span style={{
                            color: res.tyranny_index > 0.8 ? '#dc3545'
                              : res.tyranny_index > 0.4 ? '#fd7e14' : '#198754',
                            fontWeight: 700,
                          }}>
                            {Math.round(res.tyranny_index * 100)}%
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* ── Real-world safeguards ── */}
          <div className="mt-3 border rounded p-3" data-testid="safeguards-section"
            style={{ background: '#f8f9fa', fontSize: '0.78rem' }}>
            <div className="fw-semibold mb-2">{t('tyranny.safeguardsTitle')}</div>
            <Row className="g-2">
              {(['constitution', 'scotus', 'eu', 'senate'] as const).map((k) => (
                <Col key={k} xs={12} md={6}>
                  <div className="border rounded p-2" style={{ background: '#fff' }}>
                    <div className="fw-semibold" style={{ fontSize: '0.75rem' }}>
                      {t(`tyranny.safeguard_${k}_title`)}
                    </div>
                    <div className="text-muted" style={{ fontSize: '0.72rem' }}>
                      {t(`tyranny.safeguard_${k}_desc`)}
                    </div>
                  </div>
                </Col>
              ))}
            </Row>
          </div>

          {/* ── Pedagogical note ── */}
          <Alert variant="secondary" className="mt-3" style={{ fontSize: '0.8rem' }}
            data-testid="pedagogical-note">
            <strong>{t('tyranny.noteTitle')}</strong> {data.pedagogical_note}
          </Alert>
        </>
      )}
    </div>
  );
};

export default MajorityTyrannyPanel;
