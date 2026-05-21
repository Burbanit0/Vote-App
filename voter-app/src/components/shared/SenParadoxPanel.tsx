/**
 * SenParadoxPanel — demonstrates Sen's Impossibility of a Paretian Liberal (1970):
 * no social choice rule can simultaneously satisfy Pareto efficiency and
 * minimal individual liberalism.
 */
import React, { useCallback, useState } from 'react';
import axios from 'axios';
import { useTranslation } from 'react-i18next';
import { Alert, Badge, Button, Card, Col, Form, Row, Spinner } from 'react-bootstrap';

const API = process.env.REACT_APP_API_URL ?? 'http://localhost:4433';

const ALTS = ['x', 'y', 'z'] as const;

// ── Types ─────────────────────────────────────────────────────────────────────

interface ParadoxExample {
  name:                string;
  voters_preferences:  string[][];
  private_spheres:     Record<string, string[]>;
  liberal_outcome:     string;
  pareto_outcome:      string;
  conflict:            boolean;
  explanation:         string;
}

interface ResolutionOption { name: string; outcome: string; cost: string; theorist: string; }

interface SenData {
  paradox_exists:     boolean;
  paradox_examples:   ParadoxExample[];
  paradox_frequency:  number;
  alternative_names:  Record<string, string>;
  resolution_options: ResolutionOption[];
  real_world_analogy: string;
  pedagogical_note:   string;
}

// ── Conflict visualisation SVG ────────────────────────────────────────────────

interface ConflictProps { data: SenData; }

const ConflictViz: React.FC<ConflictProps> = ({ data }) => {
  const hasConflict = data.paradox_exists;
  return (
    <svg data-testid="conflict-viz-svg" width={320} height={160}
      style={{ display: 'block' }}>
      {/* Pareto node */}
      <ellipse cx={60} cy={80} rx={52} ry={30}
        fill={hasConflict ? '#dc354520' : '#19875420'} stroke={hasConflict ? '#dc3545' : '#198754'} strokeWidth={2} />
      <text x={60} y={76} textAnchor="middle" style={{ fontSize: 11, fontWeight: 700, fill: '#495057' }}>Pareto</text>
      <text x={60} y={92} textAnchor="middle" style={{ fontSize: 9, fill: '#6c757d' }}>Efficacité</text>

      {/* Liberté node */}
      <ellipse cx={260} cy={80} rx={52} ry={30}
        fill={hasConflict ? '#dc354520' : '#19875420'} stroke={hasConflict ? '#dc3545' : '#198754'} strokeWidth={2} />
      <text x={260} y={76} textAnchor="middle" style={{ fontSize: 11, fontWeight: 700, fill: '#495057' }}>Liberté</text>
      <text x={260} y={92} textAnchor="middle" style={{ fontSize: 9, fill: '#6c757d' }}>Individuelle</text>

      {/* Arrow */}
      <defs>
        <marker id="arr" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto">
          <path d="M0,0 L8,4 L0,8 Z" fill={hasConflict ? '#dc3545' : '#198754'} />
        </marker>
      </defs>
      <line x1={113} y1={70} x2={207} y2={70}
        stroke={hasConflict ? '#dc3545' : '#198754'} strokeWidth={2.5}
        markerEnd="url(#arr)" strokeDasharray={hasConflict ? '6 3' : undefined} />
      <line x1={207} y1={90} x2={113} y2={90}
        stroke={hasConflict ? '#dc3545' : '#198754'} strokeWidth={2.5}
        markerEnd="url(#arr)" strokeDasharray={hasConflict ? '6 3' : undefined} />
      <text x={160} y={64} textAnchor="middle" style={{ fontSize: 9, fill: hasConflict ? '#dc3545' : '#198754', fontWeight: 700 }}>
        {hasConflict ? '⚡ Contradiction' : '✓ Compatible'}
      </text>
    </svg>
  );
};

// ── Main panel ────────────────────────────────────────────────────────────────

const SenParadoxPanel: React.FC = () => {
  const { t } = useTranslation();

  const [seed,    setSeed]    = useState(42);
  const [data,    setData]    = useState<SenData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState<string | null>(null);

  // Interactive: user sets their own preferences for Person 1
  const [userPref1, setUserPref1] = useState(['z', 'x', 'y']);
  const [userPref2, setUserPref2] = useState(['x', 'y', 'z']);
  const [customResult, setCustomResult] = useState<ParadoxExample | null>(null);

  const runSimulation = useCallback(async () => {
    setLoading(true);
    setError(null);
    setCustomResult(null);
    try {
      const res = await axios.post(`${API}/api/theory/sen-paradox`, {
        num_voters: 2,
        seed,
        rights_definition: 'liberal',
      });
      setData(res.data);
    } catch {
      setError(t('sen.error'));
    } finally {
      setLoading(false);
    }
  }, [seed, t]);

  const testCustomPrefs = useCallback(async () => {
    if (!data) return;
    setLoading(true);
    try {
      const res = await axios.post(`${API}/api/theory/sen-paradox`, {
        num_voters: 2,
        seed,
        rights_definition: 'liberal',
      });
      // Find if the custom prefs match a paradox
      const ex = (res.data as SenData).paradox_examples;
      setCustomResult(ex.length > 0 ? ex[0] : null);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [data, seed]);

  const swapPref1 = (arr: string[], i: number, j: number) => {
    const next = [...arr]; [next[i], next[j]] = [next[j], next[i]]; setUserPref1(next);
  };
  const swapPref2 = (arr: string[], i: number, j: number) => {
    const next = [...arr]; [next[i], next[j]] = [next[j], next[i]]; setUserPref2(next);
  };

  const altLabel = (a: string) => data?.alternative_names[a] ?? a;

  return (
    <div>
      {/* Controls */}
      <Row className="g-2 mb-3 align-items-end">
        <Col xs={6} md={3}>
          <Form.Label className="small mb-0">{t('sen.seed')}</Form.Label>
          <Form.Control type="number" size="sm" value={seed}
            data-testid="seed-input"
            onChange={(e) => setSeed(Number(e.target.value))} />
        </Col>
        <Col xs="auto">
          <Button variant="primary" onClick={runSimulation} disabled={loading}
            data-testid="simulate-btn">
            {loading ? <Spinner size="sm" animation="border" /> : t('sen.run')}
          </Button>
        </Col>
      </Row>

      {!data && !loading && !error && (
        <Alert variant="info" role="alert">{t('sen.prompt')}</Alert>
      )}
      {error && <Alert variant="danger">{error}</Alert>}

      {data && (
        <>
          {/* Headline badges */}
          <div className="d-flex flex-wrap gap-2 mb-3">
            <Badge bg={data.paradox_exists ? 'danger' : 'success'}
              data-testid="paradox-badge">
              {data.paradox_exists ? t('sen.paradoxExists') : t('sen.noParadox')}
            </Badge>
            <Badge bg="warning" text="dark" data-testid="frequency-badge">
              {t('sen.frequency')}: {Math.round(data.paradox_frequency * 100)}%
            </Badge>
          </div>

          <Row className="g-3">
            <Col xs={12} md={6}>
              {/* Conflict visualisation */}
              <div className="fw-semibold mb-1" style={{ fontSize: '0.85rem' }}>{t('sen.vizTitle')}</div>
              <div className="border rounded p-2 mb-3" style={{ background: '#f8f9fa' }}>
                <ConflictViz data={data} />
              </div>

              {/* Canonical example */}
              {data.paradox_examples.length > 0 && (
                <div data-testid="paradox-example">
                  {data.paradox_examples.slice(0, 1).map((ex, i) => (
                    <Card key={i} className="border-danger mb-2">
                      <Card.Header className="py-1 bg-danger bg-opacity-10"
                        style={{ fontSize: '0.8rem', fontWeight: 700 }}>
                        ⚡ {ex.name}
                      </Card.Header>
                      <Card.Body className="py-2">
                        <div className="d-flex gap-4 mb-2" style={{ fontSize: '0.78rem' }}>
                          <div>
                            <div className="text-muted">{t('sen.person1')}:</div>
                            {ex.voters_preferences[0].map((a, j) => (
                              <div key={j}>{j + 1}. {altLabel(a)}</div>
                            ))}
                          </div>
                          <div>
                            <div className="text-muted">{t('sen.person2')}:</div>
                            {ex.voters_preferences[1].map((a, j) => (
                              <div key={j}>{j + 1}. {altLabel(a)}</div>
                            ))}
                          </div>
                        </div>
                        <div className="d-flex gap-3 mb-1" style={{ fontSize: '0.78rem' }}>
                          <div>
                            <span className="text-muted">{t('sen.liberalOutcome')}:</span>
                            <Badge bg="warning" text="dark" className="ms-1">{altLabel(ex.liberal_outcome)}</Badge>
                          </div>
                          <div>
                            <span className="text-muted">{t('sen.paretoOutcome')}:</span>
                            <Badge bg="primary" className="ms-1">{altLabel(ex.pareto_outcome)}</Badge>
                          </div>
                        </div>
                        <div className="text-danger" style={{ fontSize: '0.75rem' }}>{ex.explanation}</div>
                      </Card.Body>
                    </Card>
                  ))}
                </div>
              )}

              {/* Real world analogy */}
              <Alert variant="light" style={{ fontSize: '0.78rem', border: '1px solid #dee2e6' }}>
                🏙 <strong>{t('sen.analogyTitle')}</strong> {data.real_world_analogy}
              </Alert>
            </Col>

            <Col xs={12} md={6}>
              {/* Resolution options */}
              <div className="fw-semibold mb-2" style={{ fontSize: '0.85rem' }}>{t('sen.resolutionsTitle')}</div>
              {data.resolution_options.map((r, i) => (
                <Card key={i} className="mb-2" style={{ fontSize: '0.78rem' }}
                  data-testid={`resolution-${i}`}>
                  <Card.Body className="py-2">
                    <div className="fw-semibold">{r.name}
                      <span className="text-muted ms-2" style={{ fontSize: '0.68rem' }}>({r.theorist})</span>
                    </div>
                    <div style={{ color: '#198754' }}>✓ {r.outcome}</div>
                    <div style={{ color: '#dc3545' }}>✗ {r.cost}</div>
                  </Card.Body>
                </Card>
              ))}

              {/* Pedagogical note */}
              <Alert variant="secondary" style={{ fontSize: '0.78rem' }}>
                <strong>{t('sen.noteTitle')}</strong> {data.pedagogical_note}
              </Alert>
            </Col>
          </Row>
        </>
      )}
    </div>
  );
};

export default SenParadoxPanel;
