/**
 * ArrowExplorer — Interactive demonstration of Arrow's Impossibility Theorem.
 * For each voting method, shows which axioms are violated and provides
 * minimal counterexamples.
 */
import React, { useCallback, useState } from 'react';
import axios from 'axios';
import { useTranslation } from 'react-i18next';
import {
  Alert, Badge, Button, Card, Col, Form, Row, Spinner, Table,
} from 'react-bootstrap';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid,
  Legend, ResponsiveContainer, ReferenceLine,
} from 'recharts';

const API = process.env.REACT_APP_API_URL ?? 'http://localhost:4433';

// ── Types ─────────────────────────────────────────────────────────────────────

interface Counterexample {
  profile?:    string[][];
  without_c?:  string;
  with_c?:     string;
  spoiler?:    string;
  cycle?:      string[];
  note?:       string;
}

interface AxiomResult { violated: boolean; counterexample: Counterexample | null; }

interface ArrowData {
  method:        string;
  violations:    Record<string, AxiomResult>;
  arrow_summary: string;
  tradeoff_type: string;
}

interface IIARateData {
  method: string;
  curve:  { n_candidates: number; violation_rate: number }[];
}

// ── Axiom definitions ─────────────────────────────────────────────────────────

const AXIOMS = [
  { key: 'iia',              labelKey: 'arrow.iia',              icon: '🔗' },
  { key: 'pareto',           labelKey: 'arrow.pareto',           icon: '🤝' },
  { key: 'transitivity',     labelKey: 'arrow.transitivity',     icon: '🔄' },
  { key: 'non_dictatorship', labelKey: 'arrow.nonDictatorship',  icon: '⚖️' },
] as const;

const METHODS = [
  'plurality', 'borda', 'irv', 'schulze', 'condorcet',
  'approval', 'majority_judgment', 'kemeny_young',
];

// ── Pentagon SVG ──────────────────────────────────────────────────────────────

const CX = 110, CY = 105, R_OUT = 80, R_IN = 20;

function pentagonPoints(r: number): [number, number][] {
  return AXIOMS.map((_, i) => {
    const angle = (Math.PI * 2 * i) / AXIOMS.length - Math.PI / 2;
    return [CX + r * Math.cos(angle), CY + r * Math.sin(angle)];
  });
}

interface PentagonProps {
  violations: Record<string, AxiomResult>;
  t: (k: string) => string;
}

const AxiomPentagon: React.FC<PentagonProps> = ({ violations, t }) => {
  const outerPts = pentagonPoints(R_OUT);
  const innerPts = pentagonPoints(R_IN);
  const outerPath = outerPts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0]},${p[1]}`).join(' ') + ' Z';

  const filledPts = AXIOMS.map((ax, i) => {
    const violated = violations[ax.key]?.violated ?? false;
    return violated ? innerPts[i] : outerPts[i];
  });
  const filledPath = filledPts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0]},${p[1]}`).join(' ') + ' Z';

  return (
    <svg data-testid="arrow-pentagon" width={220} height={210} viewBox="0 0 220 210">
      {/* Spider web */}
      <path d={outerPath} fill="none" stroke="#dee2e6" strokeWidth={1} />
      {outerPts.map((p, i) => (
        <line key={i} x1={CX} y1={CY} x2={p[0]} y2={p[1]}
          stroke="#dee2e6" strokeWidth={0.8} />
      ))}

      {/* Filled area (satisfied axioms) */}
      <path d={filledPath} fill="#005CAB" fillOpacity={0.25} stroke="#005CAB" strokeWidth={1.5} />

      {/* Axiom labels */}
      {AXIOMS.map((ax, i) => {
        const violated = violations[ax.key]?.violated ?? false;
        const [px, py] = outerPts[i];
        const lx = CX + (R_OUT + 14) * Math.cos((Math.PI * 2 * i) / AXIOMS.length - Math.PI / 2);
        const ly = CY + (R_OUT + 14) * Math.sin((Math.PI * 2 * i) / AXIOMS.length - Math.PI / 2);
        return (
          <g key={ax.key}>
            <circle cx={px} cy={py} r={5}
              fill={violated ? '#dc3545' : '#198754'} />
            <text x={lx} y={ly + 4} textAnchor="middle"
              style={{ fontSize: 9, fill: violated ? '#dc3545' : '#198754', fontWeight: 600 }}>
              {ax.icon} {t(ax.labelKey).slice(0, 12)}
            </text>
          </g>
        );
      })}

      {/* Center */}
      <circle cx={CX} cy={CY} r={3} fill="#6c757d" />
    </svg>
  );
};

// ── Method comparison table (axiom matrix) ────────────────────────────────────

const KNOWN_VIOLATIONS: Record<string, Record<string, boolean>> = {
  plurality:          { iia: true,  pareto: false, transitivity: false, non_dictatorship: false },
  borda:              { iia: true,  pareto: false, transitivity: false, non_dictatorship: false },
  irv:                { iia: true,  pareto: false, transitivity: false, non_dictatorship: false },
  schulze:            { iia: true,  pareto: false, transitivity: false, non_dictatorship: false },
  condorcet:          { iia: true,  pareto: false, transitivity: true,  non_dictatorship: false },
  approval:           { iia: true,  pareto: false, transitivity: false, non_dictatorship: false },
  majority_judgment:  { iia: true,  pareto: false, transitivity: false, non_dictatorship: false },
  kemeny_young:       { iia: true,  pareto: false, transitivity: false, non_dictatorship: false },
};

const AxiomMatrix: React.FC<{ t: (k: string) => string }> = ({ t }) => (
  <div className="table-responsive" data-testid="axiom-matrix">
    <Table size="sm" hover style={{ fontSize: '0.78rem' }}>
      <thead className="table-light">
        <tr>
          <th>{t('arrow.method')}</th>
          {AXIOMS.map((ax) => (
            <th key={ax.key} style={{ textAlign: 'center' }}>{ax.icon} {t(ax.labelKey).slice(0, 6)}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {METHODS.filter((m) => m in KNOWN_VIOLATIONS).map((m) => (
          <tr key={m}>
            <td><code>{m}</code></td>
            {AXIOMS.map((ax) => {
              const violated = KNOWN_VIOLATIONS[m]?.[ax.key] ?? false;
              return (
                <td key={ax.key} style={{ textAlign: 'center' }}>
                  {violated
                    ? <span style={{ color: '#dc3545', fontWeight: 700 }}>✗</span>
                    : <span style={{ color: '#198754' }}>✓</span>}
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </Table>
  </div>
);

// ── Counterexample display ────────────────────────────────────────────────────

const CounterexampleCard: React.FC<{
  axiom: string;
  result: AxiomResult;
  t: (k: string) => string;
}> = ({ axiom, result, t }) => {
  if (!result.violated) {
    return (
      <Alert variant="success" style={{ fontSize: '0.8rem' }}>
        ✓ {t('arrow.satisfied')} — {t(`arrow.${axiom}Satisfied`)}
      </Alert>
    );
  }

  const ce = result.counterexample;
  if (!ce) {
    return (
      <Alert variant="danger" style={{ fontSize: '0.8rem' }}>
        ✗ {t('arrow.violated')} — {t(`arrow.${axiom}ViolatedGeneric`)}
      </Alert>
    );
  }

  return (
    <Card className="border-danger mb-2" data-testid={`counterexample-${axiom}`}>
      <Card.Header className="py-1 bg-danger bg-opacity-10" style={{ fontSize: '0.78rem' }}>
        ✗ {t(`arrow.${axiom}`)} — {t('arrow.counterexample')}
      </Card.Header>
      <Card.Body className="py-2">
        {axiom === 'iia' && ce.profile && (
          <>
            <div style={{ fontSize: '0.75rem', marginBottom: 8 }}>
              <strong>{t('arrow.iiaProfileTitle')}</strong>
              <div className="d-flex gap-2 flex-wrap mt-1">
                {ce.profile.map((v, i) => (
                  <Badge key={i} bg="light" text="dark"
                    style={{ fontFamily: 'monospace', fontSize: '0.7rem' }}>
                    V{i + 1}: {v.join('>')}
                  </Badge>
                ))}
              </div>
            </div>
            <div className="d-flex gap-3" style={{ fontSize: '0.78rem' }}>
              <div>
                <span className="text-muted">{t('arrow.withoutSpoiler')} ({ce.spoiler}):</span>{' '}
                <Badge bg="secondary">{ce.without_c} {t('arrow.wins')}</Badge>
              </div>
              <span>→</span>
              <div>
                <span className="text-muted">{t('arrow.withSpoiler')} ({ce.spoiler}):</span>{' '}
                <Badge bg="danger">{ce.with_c} {t('arrow.wins')}</Badge>
              </div>
            </div>
          </>
        )}
        {axiom === 'transitivity' && ce.cycle && (
          <div style={{ fontSize: '0.78rem' }}>
            <span className="text-muted">{t('arrow.cycle')}:</span>{' '}
            <code style={{ color: '#dc3545' }}>{ce.cycle.join(' > ')}</code>
          </div>
        )}
        {ce.note && (
          <div className="text-muted mt-1" style={{ fontSize: '0.72rem' }}>{ce.note}</div>
        )}
      </Card.Body>
    </Card>
  );
};

// ── Main component ────────────────────────────────────────────────────────────

const ArrowExplorer: React.FC = () => {
  const { t } = useTranslation();

  const [method,      setMethod]      = useState('plurality');
  const [data,        setData]        = useState<ArrowData | null>(null);
  const [rateData,    setRateData]    = useState<IIARateData | null>(null);
  const [loading,     setLoading]     = useState(false);
  const [rateLoading, setRateLoading] = useState(false);
  const [error,       setError]       = useState<string | null>(null);
  const [checkedAxioms, setChecked]   = useState<Set<string>>(new Set());

  const runAnalysis = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [arrowRes, rateRes] = await Promise.all([
        axios.post(`${API}/api/theory/arrow`, { method }),
        axios.post(`${API}/api/theory/iia-rate`, { method, max_candidates: 8, num_trials: 100 }),
      ]);
      setData(arrowRes.data);
      setRateData(rateRes.data);
    } catch {
      setError(t('arrow.error'));
    } finally {
      setLoading(false);
    }
  }, [method, t]);

  const toggleAxiom = (key: string) => {
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  };

  // Filter methods that satisfy all checked axioms
  const compatibleMethods = checkedAxioms.size === 0
    ? []
    : METHODS.filter((m) => {
        const v = KNOWN_VIOLATIONS[m];
        if (!v) return false;
        return [...checkedAxioms].every((ax) => !v[ax]);
      });

  return (
    <div>
      {/* Axiom filter */}
      <Card className="mb-4" data-testid="axiom-filter-section">
        <Card.Header className="fw-bold" style={{ fontSize: '0.85rem' }}>
          {t('arrow.filterTitle')}
        </Card.Header>
        <Card.Body>
          <p style={{ fontSize: '0.8rem' }}>{t('arrow.filterDesc')}</p>
          <div className="d-flex flex-wrap gap-2 mb-2">
            {AXIOMS.map((ax) => (
              <Form.Check key={ax.key} type="checkbox"
                id={`check-${ax.key}`}
                label={`${ax.icon} ${t(ax.labelKey)}`}
                checked={checkedAxioms.has(ax.key)}
                data-testid={`axiom-check-${ax.key}`}
                onChange={() => toggleAxiom(ax.key)}
                style={{ fontSize: '0.82rem' }}
              />
            ))}
          </div>
          {checkedAxioms.size > 0 && (
            <div data-testid="compatible-methods">
              {compatibleMethods.length > 0
                ? <Alert variant="success" style={{ fontSize: '0.78rem' }}>
                    ✓ {t('arrow.compatible')}: {compatibleMethods.map((m) => <code key={m} className="me-1">{m}</code>)}
                  </Alert>
                : checkedAxioms.size === AXIOMS.length
                  ? <Alert variant="danger" style={{ fontSize: '0.78rem' }}>
                      ✗ {t('arrow.noCompatible')} — {t('arrow.arrowStatement')}
                    </Alert>
                  : <Alert variant="warning" style={{ fontSize: '0.78rem' }}>
                      {t('arrow.noCompatiblePartial')}
                    </Alert>}
            </div>
          )}
        </Card.Body>
      </Card>

      {/* Method selector + analysis */}
      <Row className="g-2 mb-3 align-items-end">
        <Col xs={12} md={4}>
          <Form.Label className="small mb-0">{t('arrow.selectMethod')}</Form.Label>
          <Form.Select size="sm" value={method}
            data-testid="method-select"
            onChange={(e) => setMethod(e.target.value)}>
            {METHODS.map((m) => <option key={m} value={m}>{m}</option>)}
          </Form.Select>
        </Col>
        <Col xs="auto">
          <Button variant="primary" onClick={runAnalysis} disabled={loading}
            data-testid="analyze-btn">
            {loading ? <Spinner size="sm" animation="border" /> : t('arrow.analyze')}
          </Button>
        </Col>
      </Row>

      {error && <Alert variant="danger">{error}</Alert>}

      {data && (
        <Row className="g-4">
          {/* Pentagon */}
          <Col xs={12} md={4} className="text-center">
            <div className="fw-semibold mb-1" style={{ fontSize: '0.85rem' }}>{t('arrow.pentagonTitle')}</div>
            <AxiomPentagon violations={data.violations} t={t} />
            <Badge bg="info" text="dark" style={{ fontSize: '0.72rem' }}>
              {t(`arrow.tradeoff_${data.tradeoff_type}`)}
            </Badge>
          </Col>

          {/* Violations detail */}
          <Col xs={12} md={8}>
            <div className="fw-semibold mb-2" style={{ fontSize: '0.85rem' }}>
              {t('arrow.violationsTitle')}
            </div>
            {AXIOMS.map((ax) => (
              <CounterexampleCard key={ax.key} axiom={ax.key}
                result={data.violations[ax.key]}
                t={t} />
            ))}
            <Alert variant="secondary" style={{ fontSize: '0.8rem' }}>
              <strong>{t('arrow.summaryLabel')}</strong> {data.arrow_summary}
            </Alert>
          </Col>
        </Row>
      )}

      {/* IIA violation rate chart */}
      {rateData && (
        <div className="mt-4" data-testid="iia-rate-chart">
          <div className="fw-semibold mb-1" style={{ fontSize: '0.85rem' }}>
            {t('arrow.iiaRateTitle')}
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={rateData.curve} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="n_candidates" label={{ value: t('arrow.nCandidates'), position: 'insideBottom', offset: -2, fontSize: 10 }} />
              <YAxis domain={[0, 1]} tickFormatter={(v: number) => `${Math.round(v * 100)}%`} tick={{ fontSize: 10 }} />
              <Tooltip formatter={(v: number) => `${Math.round(v * 100)}%`} />
              <ReferenceLine y={0} stroke="#198754" strokeDasharray="4 2" />
              <Line type="monotone" dataKey="violation_rate" name={t('arrow.iiaViolationRate')}
                stroke="#dc3545" strokeWidth={2} dot />
            </LineChart>
          </ResponsiveContainer>
          <p className="text-muted" style={{ fontSize: '0.75rem' }}>{t('arrow.iiaRateDesc')}</p>
        </div>
      )}

      {/* Method comparison matrix */}
      <div className="mt-4">
        <div className="fw-semibold mb-2" style={{ fontSize: '0.85rem' }}>{t('arrow.matrixTitle')}</div>
        <AxiomMatrix t={t} />
      </div>

      {/* Key message */}
      <Alert variant="primary" className="mt-3" style={{ fontSize: '0.85rem' }}>
        <strong>🏛 {t('arrow.centralMessage')}</strong>
      </Alert>
    </div>
  );
};

export default ArrowExplorer;
