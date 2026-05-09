import React from 'react';
import { Badge, Button, Card, Col, Form, Row } from 'react-bootstrap';

export interface CandidateConfig {
  id: string;
  name: string;
  ideology: number;   // [-1, 1]
  economy: number;    // [0, 1]
  environment: number;
  social: number;
  isBlank: boolean;
}

interface Props {
  candidates: CandidateConfig[];
  onChange: (candidates: CandidateConfig[]) => void;
}

let _idCounter = 0;
export function newCandidate(name = '', ideology = 0): CandidateConfig {
  const pos = (ideology + 1) / 2;
  return {
    id: `c${++_idCounter}`,
    name,
    ideology,
    economy:     Math.round(pos * 100) / 100,
    environment: Math.round((1 - pos) * 100) / 100,
    social:      Math.round((1 - pos) * 100) / 100,
    isBlank: false,
  };
}

export function newBlankCandidate(): CandidateConfig {
  return { id: `blank${++_idCounter}`, name: 'Vote Blanc', ideology: 0, economy: 0.5, environment: 0.5, social: 0.5, isBlank: true };
}

const IDEOLOGY_LABELS = ['Extrême gauche', 'Gauche', 'Centre-gauche', 'Centre', 'Centre-droit', 'Droite', 'Extrême droite'];

function ideologyLabel(v: number): string {
  const idx = Math.round((v + 1) / 2 * (IDEOLOGY_LABELS.length - 1));
  return IDEOLOGY_LABELS[Math.max(0, Math.min(IDEOLOGY_LABELS.length - 1, idx))];
}

function ideologyColor(v: number): string {
  const t = (v + 1) / 2;
  const r = Math.round(220 * t);
  const b = Math.round(220 * (1 - t));
  return `rgb(${r},60,${b})`;
}

const CandidateEditor: React.FC<Props> = ({ candidates, onChange }) => {
  const hasBlank = candidates.some((c) => c.isBlank);

  const update = (id: string, patch: Partial<CandidateConfig>) => {
    onChange(candidates.map((c) => (c.id === id ? { ...c, ...patch } : c)));
  };

  const onIdeologyChange = (id: string, val: number) => {
    const pos = (val + 1) / 2;
    update(id, {
      ideology:    val,
      economy:     Math.round(pos * 100) / 100,
      environment: Math.round((1 - pos) * 100) / 100,
      social:      Math.round((1 - pos) * 100) / 100,
    });
  };

  const remove = (id: string) => onChange(candidates.filter((c) => c.id !== id));

  const Slider = ({ label, value, onChange: onSliderChange }: { label: string; value: number; onChange: (v: number) => void }) => (
    <div className="mb-2">
      <div className="d-flex justify-content-between mb-1">
        <small className="text-muted">{label}</small>
        <small className="fw-semibold">{Math.round(value * 100)}%</small>
      </div>
      <Form.Range min={0} max={1} step={0.05} value={value} onChange={(e) => onSliderChange(Number(e.target.value))} />
    </div>
  );

  return (
    <div>
      <p className="text-muted small mb-3">
        Définissez les candidats de votre élection. Le curseur idéologique pré-remplit les positions ; vous pouvez les ajuster.
      </p>

      {candidates.map((c) => (
        <Card key={c.id} className={`mb-3 ${c.isBlank ? 'border-warning' : ''}`}>
          <Card.Body>
            {c.isBlank ? (
              <div className="d-flex align-items-center justify-content-between">
                <div className="d-flex align-items-center gap-2">
                  <Badge bg="warning" text="dark" style={{ fontSize: '0.85rem' }}>⬜ Vote Blanc</Badge>
                  <small className="text-muted">Exprime un refus actif de tous les candidats</small>
                </div>
                <Button variant="outline-danger" size="sm" onClick={() => remove(c.id)}>✕</Button>
              </div>
            ) : (
              <>
                <Row className="g-2 align-items-center mb-3">
                  <Col md={5}>
                    <Form.Control
                      size="sm"
                      placeholder="Nom du candidat"
                      value={c.name}
                      onChange={(e) => update(c.id, { name: e.target.value })}
                    />
                  </Col>
                  <Col md={6}>
                    <div className="d-flex align-items-center gap-2">
                      <small className="text-nowrap" style={{ color: '#3c3cdc', minWidth: 50 }}>Gauche</small>
                      <Form.Range
                        min={-1} max={1} step={0.05} value={c.ideology}
                        onChange={(e) => onIdeologyChange(c.id, Number(e.target.value))}
                      />
                      <small className="text-nowrap" style={{ color: '#dc3c3c', minWidth: 50, textAlign: 'right' }}>Droite</small>
                    </div>
                    <div className="text-center mt-1">
                      <Badge style={{ backgroundColor: ideologyColor(c.ideology), fontSize: '0.72rem' }}>
                        {ideologyLabel(c.ideology)}
                      </Badge>
                    </div>
                  </Col>
                  <Col md={1} className="text-end">
                    <Button variant="outline-danger" size="sm" onClick={() => remove(c.id)}>✕</Button>
                  </Col>
                </Row>

                <Row className="g-3">
                  <Col md={4}>
                    <Slider label="💰 Économie (libéral → interventionniste)" value={c.economy} onChange={(v) => update(c.id, { economy: v })} />
                  </Col>
                  <Col md={4}>
                    <Slider label="🌿 Environnement (faible → fort)" value={c.environment} onChange={(v) => update(c.id, { environment: v })} />
                  </Col>
                  <Col md={4}>
                    <Slider label="🤝 Social (libéral → solidaire)" value={c.social} onChange={(v) => update(c.id, { social: v })} />
                  </Col>
                </Row>
              </>
            )}
          </Card.Body>
        </Card>
      ))}

      <div className="d-flex gap-2">
        <Button variant="outline-primary" size="sm" onClick={() => onChange([...candidates, newCandidate()])}>
          + Ajouter un candidat
        </Button>
        {!hasBlank && (
          <Button variant="outline-warning" size="sm" onClick={() => onChange([...candidates, newBlankCandidate()])}>
            ⬜ + Vote Blanc
          </Button>
        )}
      </div>
    </div>
  );
};

export default CandidateEditor;
