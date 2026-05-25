/**
 * AgendaManipulationPanel — demonstrates agenda manipulation power (Plott 1967):
 * by choosing the order of binary votes, an agenda-setter can produce any desired
 * outcome with the same electorate.
 */
import React, { useCallback, useRef, useState } from 'react';
import axios from 'axios';
import { useTranslation } from 'react-i18next';
import { Alert, Badge, Button, Col, Form, Row, Spinner } from 'react-bootstrap';
import { apiPath } from '../../api/apiVersion';

const API = process.env.REACT_APP_API_URL ?? 'http://localhost:4433';
const DEFAULT_ALTS = ['Alice', 'Bob', 'Carol'];

// ── Types ─────────────────────────────────────────────────────────────────────

interface AgendaData {
  pairwise_matrix:    Record<string, Record<string, number>>;
  condorcet_winner:   string | null;
  all_outcomes:       Record<string, { outcome: string; sequence: string[] }>;
  achievable_outcomes: string[];
  optimal_agenda: {
    for_target: string[];
    neutral:    string[];
    worst_case: string[];
  };
  manipulation_power: number;
  pedagogical_note:   string;
}

// ── Binary elimination (client-side) ─────────────────────────────────────────

function binaryElim(order: string[], pairwise: Record<string, Record<string, number>>): string {
  let current = order[0];
  for (let i = 1; i < order.length; i++) {
    const challenger = order[i];
    if ((pairwise[challenger]?.[current] ?? 0) > 0.5) current = challenger;
  }
  return current;
}

// ── Pairwise matrix SVG ───────────────────────────────────────────────────────

interface PairwiseProps { matrix: Record<string, Record<string, number>>; alts: string[]; }

const PairwiseMatrix: React.FC<PairwiseProps> = ({ matrix, alts }) => {
  const n = alts.length;
  const cell = 52, labelW = 60;
  const W = labelW + n * cell, H = labelW + n * cell;

  return (
    <svg data-testid="pairwise-matrix-svg" width={W} height={H}
      style={{ display: 'block', fontFamily: 'monospace' }}>
      {/* Column headers */}
      {alts.map((b, j) => (
        <text key={`ch-${j}`} x={labelW + j * cell + cell / 2} y={labelW - 6}
          textAnchor="middle" style={{ fontSize: 10, fill: '#495057', fontWeight: 600 }}>
          {b.length > 6 ? b.slice(0, 5) + '.' : b}
        </text>
      ))}
      {/* Row headers */}
      {alts.map((a, i) => (
        <text key={`rh-${i}`} x={labelW - 4} y={labelW + i * cell + cell / 2 + 4}
          textAnchor="end" style={{ fontSize: 10, fill: '#495057', fontWeight: 600 }}>
          {a.length > 6 ? a.slice(0, 5) + '.' : a}
        </text>
      ))}
      {/* Cells */}
      {alts.map((a, i) => alts.map((b, j) => {
        const val = matrix[a]?.[b] ?? 0.5;
        const isWin  = val > 0.5;
        const isLose = val < 0.5;
        const fill   = a === b ? '#f8f9fa' : isWin ? '#d1e7dd' : isLose ? '#f8d7da' : '#fff3cd';
        return (
          <g key={`${i}-${j}`}>
            <rect x={labelW + j * cell} y={labelW + i * cell}
              width={cell} height={cell} fill={fill} stroke="#dee2e6" />
            {a !== b && (
              <text x={labelW + j * cell + cell / 2} y={labelW + i * cell + cell / 2 + 4}
                textAnchor="middle" style={{ fontSize: 11, fill: isWin ? '#198754' : isLose ? '#dc3545' : '#856404' }}>
                {Math.round(val * 100)}%
              </text>
            )}
          </g>
        );
      }))}
      {/* Corner label */}
      <text x={labelW - 4} y={labelW - 6} textAnchor="end" style={{ fontSize: 9, fill: '#adb5bd' }}>
        A→B%
      </text>
    </svg>
  );
};

// ── Draggable agenda editor ───────────────────────────────────────────────────

interface AgendaEditorProps {
  order:     string[];
  onReorder: (next: string[]) => void;
  result:    string;
  t:         (k: string) => string;
}

const AgendaEditor: React.FC<AgendaEditorProps> = ({ order, onReorder, result, t }) => {
  const dragIdx = useRef<number | null>(null);
  return (
    <div data-testid="agenda-editor">
      {order.map((alt, i) => (
        <div key={alt}
          draggable
          onDragStart={() => { dragIdx.current = i; }}
          onDragOver={(e) => e.preventDefault()}
          onDrop={() => {
            if (dragIdx.current == null || dragIdx.current === i) return;
            const next = [...order];
            const [moved] = next.splice(dragIdx.current, 1);
            next.splice(i, 0, moved);
            dragIdx.current = null;
            onReorder(next);
          }}
          style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '8px 12px', marginBottom: 4,
            background: '#f8f9fa', border: '1px solid #dee2e6', borderRadius: 6,
            cursor: 'grab', fontSize: '0.85rem',
          }}
        >
          <span style={{ color: '#adb5bd', minWidth: 18 }}>{i + 1}.</span>
          <span style={{ flex: 1 }}>{alt}</span>
          {i === 0 && <Badge bg="secondary" style={{ fontSize: '0.6rem' }}>{t('agenda.champion')}</Badge>}
          {i > 0 && <Badge bg="light" text="dark" style={{ fontSize: '0.6rem' }}>vs {t('agenda.champion')}</Badge>}
          <span style={{ color: '#adb5bd', fontSize: '0.7rem' }}>⠿</span>
        </div>
      ))}
      <div className="mt-2 p-2 rounded" style={{ background: '#e8f5e9', border: '1px solid #c8e6c9' }}>
        <span style={{ fontSize: '0.82rem', fontWeight: 700 }}>
          🏆 {t('agenda.result')}: <span style={{ color: '#198754' }}>{result}</span>
        </span>
      </div>
      <div className="text-muted mt-1" style={{ fontSize: '0.7rem' }}>{t('agenda.dragHint')}</div>
    </div>
  );
};

// ── Main panel ────────────────────────────────────────────────────────────────

const AgendaManipulationPanel: React.FC = () => {
  const { t } = useTranslation();

  const [data,      setData]      = useState<AgendaData | null>(null);
  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState<string | null>(null);
  const [alts,      setAlts]      = useState<string[]>(DEFAULT_ALTS);
  const [agendaOrder, setAgendaOrder] = useState<string[]>(DEFAULT_ALTS);
  const [numVoters, setNumVoters] = useState(21);
  const [seed,      setSeed]      = useState(42);
  const [target,    setTarget]    = useState(DEFAULT_ALTS[0]);

  const runSimulation = useCallback(async (as: string[], nv: number, sd: number, tgt: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.post(`${API}${apiPath('theory/agenda-manipulation')}`, {
        alternatives: as, num_voters: nv, seed: sd, target_outcome: tgt,
        constraint_type: 'binary_elimination',
      });
      setData(res.data);
      setAgendaOrder([...as]); // reset to default
    } catch {
      setError(t('agenda.error'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  const handleSimulate = () => runSimulation(alts, numVoters, seed, target);

  const animateTo = (orderKey: 'for_target' | 'neutral' | 'worst_case') => {
    if (!data) return;
    setAgendaOrder([...data.optimal_agenda[orderKey]]);
  };

  const currentResult = data ? binaryElim(agendaOrder, data.pairwise_matrix) : '';

  return (
    <div>
      {/* Controls */}
      <Row className="g-2 mb-3 align-items-end">
        <Col xs={6} md={2}>
          <Form.Label className="small mb-0">{t('agenda.voters')}</Form.Label>
          <Form.Control type="number" size="sm" min={3} max={101} value={numVoters}
            data-testid="voters-input"
            onChange={(e) => setNumVoters(Number(e.target.value))} />
        </Col>
        <Col xs={6} md={2}>
          <Form.Label className="small mb-0">{t('agenda.seed')}</Form.Label>
          <Form.Control type="number" size="sm" value={seed}
            data-testid="seed-input"
            onChange={(e) => setSeed(Number(e.target.value))} />
        </Col>
        <Col xs={12} md={3}>
          <Form.Label className="small mb-0">{t('agenda.target')}</Form.Label>
          <Form.Select size="sm" value={target} data-testid="target-select"
            onChange={(e) => setTarget(e.target.value)}>
            {alts.map((a) => <option key={a} value={a}>{a}</option>)}
          </Form.Select>
        </Col>
        <Col xs="auto">
          <Button variant="primary" onClick={handleSimulate} disabled={loading}
            data-testid="simulate-btn">
            {loading ? <Spinner size="sm" animation="border" /> : t('agenda.run')}
          </Button>
        </Col>
      </Row>

      {!data && !loading && !error && (
        <Alert variant="info" role="alert">{t('agenda.prompt')}</Alert>
      )}
      {error && <Alert variant="danger">{error}</Alert>}

      {data && (
        <>
          {/* Condorcet + manipulation power badges */}
          <div className="d-flex flex-wrap gap-2 mb-3">
            <Badge bg={data.condorcet_winner ? 'success' : 'danger'}
              data-testid="cw-badge">
              {data.condorcet_winner
                ? `✓ ${t('agenda.cwExists')}: ${data.condorcet_winner}`
                : `✗ ${t('agenda.noCW')}`}
            </Badge>
            <Badge
              bg={data.manipulation_power >= 0.99 ? 'danger' : data.manipulation_power > 0.5 ? 'warning' : 'secondary'}
              text={data.manipulation_power > 0.5 && data.manipulation_power < 0.99 ? 'dark' : undefined}
              data-testid="power-badge">
              {t('agenda.manipPower')}: {Math.round(data.manipulation_power * 100)}%
            </Badge>
          </div>

          <Row className="g-3">
            {/* Agenda editor */}
            <Col xs={12} md={5}>
              <div className="fw-semibold mb-1" style={{ fontSize: '0.85rem' }}>
                {t('agenda.editorTitle')}
              </div>
              <AgendaEditor
                order={agendaOrder}
                onReorder={setAgendaOrder}
                result={currentResult}
                t={t}
              />
              {/* Quick-set buttons */}
              <div className="d-flex gap-2 mt-2 flex-wrap">
                <Button size="sm" variant="outline-success"
                  data-testid="btn-make-target-win"
                  onClick={() => animateTo('for_target')}>
                  🎯 {t('agenda.makeTargetWin', { target })}
                </Button>
                <Button size="sm" variant="outline-secondary"
                  data-testid="btn-neutral"
                  onClick={() => animateTo('neutral')}>
                  ⚖️ {t('agenda.neutral')}
                </Button>
              </div>
            </Col>

            {/* Pairwise matrix */}
            <Col xs={12} md={7}>
              <div className="fw-semibold mb-1" style={{ fontSize: '0.85rem' }}>
                {t('agenda.matrixTitle')}
              </div>
              <div className="border rounded" style={{ background: '#f8f9fa', overflow: 'auto' }}>
                <PairwiseMatrix matrix={data.pairwise_matrix} alts={alts} />
              </div>
              <div className="text-muted mt-1" style={{ fontSize: '0.72rem' }}>
                {t('agenda.matrixDesc')}
              </div>
            </Col>
          </Row>

          {/* Achievable outcomes */}
          <div className="mt-3" data-testid="achievable-section">
            <div className="fw-semibold mb-1" style={{ fontSize: '0.85rem' }}>
              {t('agenda.achievableTitle')}
            </div>
            <div className="d-flex gap-2 flex-wrap">
              {alts.map((a) => {
                const possible = data.achievable_outcomes.includes(a);
                return (
                  <Badge key={a}
                    bg={possible ? 'success' : 'secondary'}
                    data-testid={`achievable-badge-${a}`}
                    style={{ fontSize: '0.78rem', padding: '6px 10px' }}>
                    {a} {possible ? '✓' : '✗'}
                  </Badge>
                );
              })}
            </div>
            {data.achievable_outcomes.length === alts.length && !data.condorcet_winner && (
              <Alert variant="danger" className="mt-2 py-1" style={{ fontSize: '0.78rem' }}
                data-testid="full-manipulation-alert">
                ⚡ {t('agenda.fullManipulation')}
              </Alert>
            )}
          </div>

          {/* Defense section */}
          <div className="mt-3 border rounded p-3" data-testid="defense-section"
            style={{ background: '#f8f9fa', fontSize: '0.78rem' }}>
            <div className="fw-semibold mb-1">{t('agenda.defenseTitle')}</div>
            <ul className="mb-0" style={{ paddingLeft: 16 }}>
              <li>{t('agenda.defense1')}</li>
              <li>{t('agenda.defense2')}</li>
              <li>{t('agenda.defense3')}</li>
            </ul>
            <div className="text-muted mt-1">{t('agenda.defenseNote')}</div>
          </div>

          {/* Pedagogical note */}
          <Alert variant="secondary" className="mt-3" style={{ fontSize: '0.8rem' }}>
            <strong>{t('agenda.noteTitle')}</strong> {data.pedagogical_note}
          </Alert>
        </>
      )}
    </div>
  );
};

export default AgendaManipulationPanel;
