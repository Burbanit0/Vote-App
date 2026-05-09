import React, { useMemo } from 'react';
import { Card, Col, Form, Row } from 'react-bootstrap';
import { Area, AreaChart, ResponsiveContainer, XAxis } from 'recharts';

export interface ElectorateState {
  numVoters: number;
  ideologyPreset: 'polarized' | 'centrist' | 'left' | 'right' | 'random';
  dissatisfactionRate: number; // [0, 1]
}

interface Props {
  config: ElectorateState;
  onChange: (patch: Partial<ElectorateState>) => void;
}

// ── Distribution curve data ────────────────────────────────────────────────

function normalPDF(x: number, mean: number, std: number): number {
  return Math.exp(-0.5 * ((x - mean) / std) ** 2) / (std * Math.sqrt(2 * Math.PI));
}

const N = 41;
const xs = Array.from({ length: N }, (_, i) => -1 + i * 0.05);

function makeCurve(fn: (x: number) => number) {
  const raw = xs.map(fn);
  const max = Math.max(...raw);
  return xs.map((x, i) => ({ x: x.toFixed(2), y: max > 0 ? raw[i] / max : 0.5 }));
}

const PRESETS: Record<ElectorateState['ideologyPreset'], { label: string; color: string; desc: string; data: ReturnType<typeof makeCurve> }> = {
  polarized: {
    label: 'Polarisée',
    color: '#e15759',
    desc: 'Deux camps opposés, peu de centristes',
    data: makeCurve((x) => normalPDF(x, -0.65, 0.2) + normalPDF(x, 0.65, 0.2)),
  },
  centrist: {
    label: 'Centriste',
    color: '#59a14f',
    desc: 'La majorité des électeurs au centre',
    data: makeCurve((x) => normalPDF(x, 0, 0.25)),
  },
  left: {
    label: 'Majorité gauche',
    color: '#4e79a7',
    desc: 'Électorat penché à gauche',
    data: makeCurve((x) => normalPDF(x, -0.35, 0.3)),
  },
  right: {
    label: 'Majorité droite',
    color: '#f28e2b',
    desc: 'Électorat penché à droite',
    data: makeCurve((x) => normalPDF(x, 0.35, 0.3)),
  },
  random: {
    label: 'Aléatoire',
    color: '#76b7b2',
    desc: 'Distribution uniforme sans tendance',
    data: makeCurve(() => 1),
  },
};

// ── Component ──────────────────────────────────────────────────────────────

const ElectorateConfig: React.FC<Props> = ({ config, onChange }) => {
  const selected = PRESETS[config.ideologyPreset];

  const dissatisfactionLabel = useMemo(() => {
    const pct = Math.round(config.dissatisfactionRate * 100);
    if (pct < 15) return `${pct}% — Électorat satisfait des candidats`;
    if (pct < 40) return `${pct}% — Insatisfaction modérée`;
    if (pct < 65) return `${pct}% — Insatisfaction élevée`;
    return `${pct}% — Crise de représentation`;
  }, [config.dissatisfactionRate]);

  return (
    <div>
      <p className="text-muted small mb-3">
        Définissez la taille et la structure idéologique de votre électorat.
      </p>

      {/* Voter count */}
      <Card className="mb-4">
        <Card.Body>
          <Form.Label>
            Nombre d'électeurs : <strong>{config.numVoters.toLocaleString()}</strong>
          </Form.Label>
          <Form.Range
            min={100} max={10000} step={100} value={config.numVoters}
            onChange={(e) => onChange({ numVoters: Number(e.target.value) })}
          />
          <div className="d-flex justify-content-between">
            <small className="text-muted">100</small>
            <small className="text-muted">10 000</small>
          </div>
        </Card.Body>
      </Card>

      {/* Ideology preset */}
      <p className="fw-semibold mb-2">Distribution idéologique</p>
      <Row className="g-2 mb-4">
        {(Object.entries(PRESETS) as [ElectorateState['ideologyPreset'], typeof PRESETS[keyof typeof PRESETS]][]).map(([key, preset]) => (
          <Col xs={6} md={4} key={key}>
            <Card
              className={`h-100 ${config.ideologyPreset === key ? 'border-primary' : ''}`}
              style={{ cursor: 'pointer', transition: 'border-color 0.15s' }}
              onClick={() => onChange({ ideologyPreset: key })}
            >
              <Card.Body className="p-2">
                <div className="d-flex align-items-center gap-1 mb-1">
                  {config.ideologyPreset === key && (
                    <span style={{ color: preset.color, fontWeight: 700 }}>●</span>
                  )}
                  <small className="fw-semibold">{preset.label}</small>
                </div>
                <ResponsiveContainer width="100%" height={50}>
                  <AreaChart data={preset.data} margin={{ top: 2, right: 2, bottom: 0, left: 2 }}>
                    <XAxis dataKey="x" hide />
                    <Area
                      type="monotone" dataKey="y"
                      stroke={preset.color}
                      fill={preset.color}
                      fillOpacity={config.ideologyPreset === key ? 0.4 : 0.15}
                      strokeWidth={config.ideologyPreset === key ? 2 : 1}
                      dot={false} isAnimationActive={false}
                    />
                  </AreaChart>
                </ResponsiveContainer>
                <div className="d-flex justify-content-between mt-1">
                  <small style={{ fontSize: '0.65rem', color: '#6c757d' }}>← G</small>
                  <small style={{ fontSize: '0.65rem', color: '#6c757d' }}>D →</small>
                </div>
                <small className="text-muted d-block mt-1" style={{ fontSize: '0.72rem' }}>{preset.desc}</small>
              </Card.Body>
            </Card>
          </Col>
        ))}
      </Row>

      {/* Dissatisfaction rate */}
      <Card>
        <Card.Body>
          <Form.Label>
            Taux d'insatisfaction générale
            <span className="text-muted ms-2" style={{ fontSize: '0.85rem' }}>
              — influence la probabilité de vote blanc
            </span>
          </Form.Label>
          <Form.Range
            min={0} max={1} step={0.05} value={config.dissatisfactionRate}
            onChange={(e) => onChange({ dissatisfactionRate: Number(e.target.value) })}
          />
          <small className="text-muted">{dissatisfactionLabel}</small>
          <div className="mt-2">
            <small className="text-info">
              ℹ️ Plus l'insatisfaction est haute, plus les électeurs placeront "Vote Blanc" en tête de leur classement.
            </small>
          </div>
        </Card.Body>
      </Card>
    </div>
  );
};

export default ElectorateConfig;
