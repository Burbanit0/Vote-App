/**
 * QuadraticFundingPage — dedicated page at /quadratic-funding
 * showcasing the QF mechanism for public goods allocation.
 */
import React, { useCallback, useRef, useState } from 'react';
import axios from 'axios';
import { useTranslation } from 'react-i18next';
import {
  Alert, Badge, Button, Card, Col, Container, Form, Row, Spinner,
} from 'react-bootstrap';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, Cell, ResponsiveContainer, Legend,
} from 'recharts';
import { useMetaTags } from '../hooks/useMetaTags';

const API = process.env.REACT_APP_API_URL ?? 'http://localhost:4433';
const DEBOUNCE_MS = 400;

// ── Types ─────────────────────────────────────────────────────────────────────

interface ProjectResult {
  name:            string;
  private_funding: number;
  matching:        number;
  total:           number;
  qf_score:        number;
}

interface QFData {
  projects:             ProjectResult[];
  winner:               string;
  mechanism_comparison: Record<string, Record<string, number>>;
  gini_coefficients:    Record<string, number>;
  vote_shares:          Record<string, number>;
  matching_pool:        number;
  budget_per_voter:     number;
  pedagogical_note:     string;
}

// ── Project editor row ────────────────────────────────────────────────────────

interface Project { name: string; x: number }

const DEFAULT_PROJECTS: Project[] = [
  { name: 'Éducation',     x: -0.4 },
  { name: 'Santé',         x:  0.0 },
  { name: 'Infrastructure', x:  0.5 },
  { name: 'Environnement', x: -0.6 },
];

// ── Colour palette ────────────────────────────────────────────────────────────

const PALETTE = ['#005CAB', '#C8590A', '#007A33', '#6c757d', '#9b59b6', '#e67e22', '#2A9D8F', '#E76F51'];
function projColor(name: string, names: string[]) {
  return PALETTE[names.indexOf(name) % PALETTE.length] ?? '#888';
}

const MECHANISM_LABELS: Record<string, string> = {
  '1p1v':        '1 Personne 1 Vote',
  'proportional': 'Proportionnel',
  'qf':           'Quadratic Funding',
};

const MECHANISM_COLORS: Record<string, string> = {
  '1p1v':        '#6c757d',
  'proportional': '#005CAB',
  'qf':           '#007A33',
};

// ── Mini bar chart for one mechanism ─────────────────────────────────────────

const MechChart: React.FC<{
  mechanism:   string;
  data:        QFData;
  poolSize:    number;
}> = ({ mechanism, data, poolSize }) => {
  const { t } = useTranslation();
  const alloc = data.mechanism_comparison[mechanism] ?? {};
  const names = data.projects.map(p => p.name);
  const chartData = names.map(name => ({
    name:    name.length > 8 ? name.slice(0, 8) + '…' : name,
    fullName: name,
    private: data.projects.find(p => p.name === name)?.private_funding ?? 0,
    matching: Math.max(0, (alloc[name] ?? 0) - (data.projects.find(p => p.name === name)?.private_funding ?? 0)),
  }));
  const gini = data.gini_coefficients[mechanism] ?? 0;
  const winner = names.reduce((best, n) =>
    (alloc[n] ?? 0) > (alloc[best] ?? 0) ? n : best, names[0]);

  return (
    <div data-testid={`mech-chart-${mechanism}`}>
      <div className="text-center fw-semibold mb-1" style={{ fontSize: '0.8rem' }}>
        {MECHANISM_LABELS[mechanism]}
      </div>
      <div style={{ height: 180 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 4, right: 4, bottom: 20, left: -10 }}>
            <XAxis dataKey="name" tick={{ fontSize: 9 }} angle={-20} textAnchor="end" />
            <YAxis tick={{ fontSize: 9 }} />
            <Tooltip
              formatter={(v: number, name: string) => [
                `€${v.toFixed(0)}`,
                name === 'private' ? 'Dons privés' : 'Matching pool',
              ]}
              labelFormatter={(l) => chartData.find(d => d.name === l)?.fullName ?? l}
            />
            <Bar dataKey="private" stackId="a" name="private"
              isAnimationActive={false}>
              {chartData.map((entry, i) => (
                <Cell key={i} fill={projColor(entry.fullName, names)} fillOpacity={0.55} />
              ))}
            </Bar>
            <Bar dataKey="matching" stackId="a" name="matching"
              isAnimationActive={false}>
              {chartData.map((entry, i) => (
                <Cell key={i} fill={projColor(entry.fullName, names)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="d-flex justify-content-between mt-1" style={{ fontSize: '0.7rem' }}>
        <Badge bg="secondary" data-testid={`gini-badge-${mechanism}`} style={{ fontSize: '0.65rem' }}>
          Gini: {gini.toFixed(2)}
        </Badge>
        <span style={{ color: projColor(winner, names), fontWeight: 600, fontSize: '0.7rem' }}>
          ✓ {winner}
        </span>
      </div>
    </div>
  );
};

// ── Main component ────────────────────────────────────────────────────────────

const QuadraticFundingPage: React.FC = () => {
  const { t } = useTranslation();
  useMetaTags({ title: 'Vote Lab — Quadratic Funding' });

  const [projects,     setProjects]     = useState<Project[]>(DEFAULT_PROJECTS);
  const [matchingPool, setMatchingPool] = useState(10000);
  const [numVoters,    setNumVoters]    = useState(100);
  const [budgetPV,     setBudgetPV]     = useState(100);
  const [ideology,     setIdeology]     = useState('random');
  const [data,         setData]         = useState<QFData | null>(null);
  const [loading,      setLoading]      = useState(false);
  const [error,        setError]        = useState<string | null>(null);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const run = useCallback(async (pool: number) => {
    setLoading(true); setError(null);
    try {
      const res = await axios.post(`${API}/api/election/quadratic-funding`, {
        projects:         projects.map(p => ({ name: p.name, x: p.x })),
        num_voters:       numVoters,
        budget_per_voter: budgetPV,
        matching_pool:    pool,
        ideology,
        seed:             42,
      });
      setData(res.data);
    } catch {
      setError(t('qf.error'));
    } finally {
      setLoading(false);
    }
  }, [projects, numVoters, budgetPV, ideology, t]);

  const handlePoolChange = (v: number) => {
    setMatchingPool(v);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => run(v), DEBOUNCE_MS);
  };

  const updateProject = (idx: number, patch: Partial<Project>) => {
    setProjects(prev => prev.map((p, i) => i === idx ? { ...p, ...patch } : p));
  };

  const addProject = () => {
    if (projects.length >= 8) return;
    setProjects(prev => [...prev, { name: `Projet ${prev.length + 1}`, x: 0 }]);
  };

  const removeProject = (idx: number) => {
    if (projects.length <= 2) return;
    setProjects(prev => prev.filter((_, i) => i !== idx));
  };

  const projNames = projects.map(p => p.name);

  return (
    <Container className="py-4" style={{ maxWidth: 1100 }}>
      <div className="mb-4">
        <h1 className="fw-bold" style={{ fontSize: '1.5rem' }}>
          💰 {t('qf.pageTitle')}
        </h1>
        <p className="text-muted" style={{ fontSize: '0.9rem', maxWidth: 700 }}>
          {t('qf.pageSubtitle')}
        </p>
      </div>

      <Row className="g-4">
        {/* Left: configuration */}
        <Col xs={12} md={4}>
          <Card>
            <Card.Header className="py-2">
              <strong style={{ fontSize: '0.85rem' }}>{t('qf.configTitle')}</strong>
            </Card.Header>
            <Card.Body className="p-3">
              {/* Projects */}
              <div className="mb-3">
                <div className="fw-semibold mb-2" style={{ fontSize: '0.8rem' }}>
                  {t('qf.projects')}
                </div>
                {projects.map((p, i) => (
                  <div key={i} className="border rounded p-2 mb-2"
                    style={{ borderLeft: `3px solid ${projColor(p.name, projNames)}`, fontSize: '0.78rem' }}>
                    <div className="d-flex gap-1 mb-1">
                      <Form.Control
                        size="sm" value={p.name}
                        onChange={e => updateProject(i, { name: e.target.value })}
                        style={{ fontSize: '0.75rem' }}
                      />
                      {projects.length > 2 && (
                        <Button size="sm" variant="outline-danger"
                          style={{ fontSize: '0.65rem', padding: '1px 5px' }}
                          onClick={() => removeProject(i)}>✕</Button>
                      )}
                    </div>
                    <Form.Label className="small mb-0">
                      Position idéologique: {p.x.toFixed(2)}
                    </Form.Label>
                    <Form.Range min={-1} max={1} step={0.05} value={p.x}
                      onChange={e => updateProject(i, { x: Number(e.target.value) })} />
                  </div>
                ))}
                {projects.length < 8 && (
                  <Button size="sm" variant="outline-secondary" className="w-100"
                    onClick={addProject} style={{ fontSize: '0.75rem' }}>
                    + {t('qf.addProject')}
                  </Button>
                )}
              </div>

              {/* Electorate */}
              <Form.Label className="small mb-0">
                {t('qf.numVoters')}: <strong>{numVoters}</strong>
              </Form.Label>
              <Form.Range min={20} max={300} step={10} value={numVoters}
                onChange={e => setNumVoters(Number(e.target.value))} className="mb-2" />

              <Form.Label className="small mb-0">
                {t('qf.budgetPerVoter')}: <strong>€{budgetPV}</strong>
              </Form.Label>
              <Form.Range min={10} max={500} step={10} value={budgetPV}
                onChange={e => setBudgetPV(Number(e.target.value))} className="mb-2" />

              <Form.Label className="small mb-1">{t('qf.ideology')}</Form.Label>
              <Form.Select size="sm" value={ideology}
                onChange={e => setIdeology(e.target.value)} className="mb-3">
                {['random', 'centrist', 'polarized', 'left_skewed', 'right_skewed'].map(v => (
                  <option key={v} value={v}>{v}</option>
                ))}
              </Form.Select>

              <Button variant="primary" className="w-100" onClick={() => run(matchingPool)}
                disabled={loading}>
                {loading ? <Spinner size="sm" /> : `💰 ${t('qf.simulate')}`}
              </Button>

              {error && <Alert variant="danger" className="mt-2 py-2" style={{ fontSize: '0.8rem' }}>{error}</Alert>}
            </Card.Body>
          </Card>
        </Col>

        {/* Right: results */}
        <Col xs={12} md={8}>
          {!data && !loading && (
            <Alert variant="info">{t('qf.prompt')}</Alert>
          )}

          {data && (
            <>
              {/* Matching pool slider */}
              <div className="border rounded p-3 mb-3">
                <Form.Label className="fw-semibold mb-0" style={{ fontSize: '0.85rem' }}>
                  {t('qf.matchingPool')}: <strong>€{matchingPool.toLocaleString()}</strong>
                  {loading && <Spinner size="sm" className="ms-2" />}
                </Form.Label>
                <Form.Range
                  min={0} max={50000} step={500} value={matchingPool}
                  onChange={e => handlePoolChange(Number(e.target.value))}
                  data-testid="pool-slider"
                />
                <div className="d-flex justify-content-between"
                  style={{ fontSize: '0.68rem', color: '#6c757d', marginTop: -4 }}>
                  <span>€0</span><span>€50 000</span>
                </div>
              </div>

              {/* Pedagogical note */}
              <Alert variant="success" className="py-2 mb-3" style={{ fontSize: '0.82rem' }}
                data-testid="qf-pedagogical">
                {data.pedagogical_note}
              </Alert>

              {/* 3 mechanism bar charts */}
              <Row className="g-3 mb-3">
                {['1p1v', 'proportional', 'qf'].map(m => (
                  <Col key={m} xs={12} sm={4}>
                    <div className="border rounded p-2">
                      <MechChart mechanism={m} data={data} poolSize={matchingPool} />
                    </div>
                  </Col>
                ))}
              </Row>

              {/* Legend — private vs matching */}
              <div className="d-flex gap-3 mb-3" style={{ fontSize: '0.72rem' }}>
                <span className="d-flex align-items-center gap-1">
                  <span style={{ width: 12, height: 12, background: '#adb5bd', display: 'inline-block', borderRadius: 2 }} />
                  {t('qf.privateFunding')}
                </span>
                <span className="d-flex align-items-center gap-1">
                  <span style={{ width: 12, height: 12, background: '#212529', display: 'inline-block', borderRadius: 2 }} />
                  {t('qf.matchingFunding')}
                </span>
              </div>

              {/* Project colour legend */}
              <div className="d-flex flex-wrap gap-2 mb-3">
                {projNames.map(n => (
                  <span key={n} className="d-flex align-items-center gap-1"
                    style={{ fontSize: '0.72rem' }}>
                    <span style={{ width: 10, height: 10, background: projColor(n, projNames), borderRadius: 2, display: 'inline-block' }} />
                    {n}
                  </span>
                ))}
              </div>

              {/* Gini comparison */}
              <div className="d-flex flex-wrap gap-2">
                <span className="small text-muted fw-semibold">{t('qf.giniLabel')}:</span>
                {(['1p1v', 'proportional', 'qf'] as const).map(m => (
                  <Badge key={m}
                    bg={data.gini_coefficients[m] < 0.2 ? 'success' : data.gini_coefficients[m] < 0.4 ? 'warning' : 'danger'}
                    text={data.gini_coefficients[m] >= 0.2 && data.gini_coefficients[m] < 0.4 ? 'dark' : undefined}
                    style={{ fontSize: '0.7rem' }}>
                    {MECHANISM_LABELS[m]}: {data.gini_coefficients[m].toFixed(2)}
                  </Badge>
                ))}
              </div>

              {/* Key insight box */}
              <div className="mt-3 rounded p-3"
                style={{ background: '#f8f9fa', border: '1px solid #dee2e6', fontSize: '0.8rem' }}>
                <div className="fw-semibold mb-1">💡 {t('qf.insightTitle')}</div>
                <p className="mb-1">{t('qf.insight1')}</p>
                <code style={{ fontSize: '0.75rem' }}>
                  50 donateurs × √2€ → (50×√2)² = 5 000 pts
                </code>
                <br />
                <code style={{ fontSize: '0.75rem' }}>
                  1 donateur × √100€ → (1×√100)² = 100 pts
                </code>
                <p className="mb-0 mt-1" style={{ color: '#6c757d' }}>{t('qf.insight2')}</p>
              </div>
            </>
          )}
        </Col>
      </Row>
    </Container>
  );
};

export default QuadraticFundingPage;
