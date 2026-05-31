/**
 * JudgmentAggregationPanel — demonstrates the discursive dilemma (List & Pettit 2002):
 * majority rule on logically linked propositions can produce collectively incoherent
 * results even when every individual voter is perfectly coherent.
 */
import React, { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, Badge, Button, Card, Col, Form, Row, Spinner, Table } from 'react-bootstrap';
import { $api } from '../../api/hooks';

// ── Types ─────────────────────────────────────────────────────────────────────

interface Proposition {
  text:            string;
  type:            string;
  id:              string;
  yes_pct:         number;
  collective_vote: boolean;
}

interface Incoherence { premises: string[]; conclusion: string; problem: string; }

interface JudgData {
  scenario:              string;
  scenario_name:         string;
  propositions:          Proposition[];
  collective_coherent:   boolean;
  incoherences:          Incoherence[];
  voter_coherence_rate:  number;
  paradox_severity:      number;
  resolution_methods: {
    premise_based:    Record<string, boolean>;
    conclusion_based: Record<string, boolean>;
  };
  pedagogical_note: string;
}

// ── Logic Tree SVG ────────────────────────────────────────────────────────────

const SVG_W = 400, SVG_H = 220;

interface TreeProps {
  data:         JudgData;
  incoherences: Incoherence[];
}

const LogicTreeSVG: React.FC<TreeProps> = ({ data, incoherences }) => {
  const premises    = data.propositions.filter((p) => p.type === 'premise');
  const conclusions = data.propositions.filter((p) => p.type === 'conclusion');
  const incoSet     = new Set(incoherences.flatMap((inc) => [...inc.premises, inc.conclusion]));

  const nodeColor = (p: Proposition) => {
    if (!p.collective_vote) return '#dc3545';  // majority no
    return '#198754';                          // majority yes
  };

  const px   = 40;
  const cxPos = SVG_W - 100;
  const stepY = premises.length > 1 ? (SVG_H - 40) / (premises.length - 1) : SVG_H / 2;

  return (
    <svg data-testid="logic-tree-svg" width={SVG_W} height={SVG_H}
      style={{ display: 'block' }}>
      {/* Premise nodes */}
      {premises.map((p, i) => {
        const py = premises.length === 1 ? SVG_H / 2 : 20 + i * stepY;
        const col = nodeColor(p);
        const isInco = incoSet.has(p.id);
        return (
          <g key={p.id}>
            <rect x={px} y={py - 16} width={130} height={32}
              rx={6} fill={col} fillOpacity={0.15}
              stroke={isInco ? '#dc3545' : col} strokeWidth={isInco ? 2.5 : 1.5} />
            <text x={px + 65} y={py + 4} textAnchor="middle"
              style={{ fontSize: 9, fill: col, fontWeight: 600 }}>
              {p.id}: {p.collective_vote ? 'OUI' : 'NON'}
            </text>
            <text x={px + 65} y={py + 14} textAnchor="middle"
              style={{ fontSize: 7, fill: '#6c757d' }}>
              {p.text.length > 22 ? p.text.slice(0, 20) + '…' : p.text}
            </text>
            {/* Edge to conclusion */}
            {conclusions.map((c, ci) => {
              const cy = SVG_H / 2;
              const edgeCol = isInco && incoSet.has(c.id) ? '#dc3545' : '#adb5bd';
              return (
                <line key={`e-${p.id}-${c.id}`}
                  x1={px + 130} y1={py}
                  x2={cxPos} y2={cy}
                  stroke={edgeCol} strokeWidth={isInco && incoSet.has(c.id) ? 2 : 1}
                  strokeDasharray={isInco && incoSet.has(c.id) ? undefined : '4 2'}
                />
              );
            })}
          </g>
        );
      })}

      {/* Conclusion nodes */}
      {conclusions.map((c, ci) => {
        const cy = SVG_H / 2;
        const col = nodeColor(c);
        const isInco = incoSet.has(c.id);
        return (
          <g key={c.id}>
            <rect x={cxPos} y={cy - 18} width={130} height={36}
              rx={6} fill={col} fillOpacity={0.18}
              stroke={isInco ? '#dc3545' : col} strokeWidth={isInco ? 3 : 1.5} />
            <text x={cxPos + 65} y={cy - 4} textAnchor="middle"
              style={{ fontSize: 9, fill: col, fontWeight: 700 }}>
              {c.id}: {c.collective_vote ? 'OUI' : 'NON'}
            </text>
            <text x={cxPos + 65} y={cy + 7} textAnchor="middle"
              style={{ fontSize: 7, fill: '#6c757d' }}>
              {c.text.length > 22 ? c.text.slice(0, 20) + '…' : c.text}
            </text>
            {isInco && (
              <text x={cxPos + 65} y={cy + 19} textAnchor="middle"
                style={{ fontSize: 8, fill: '#dc3545', fontWeight: 700 }}>⚡ INCOHÉRENT</text>
            )}
          </g>
        );
      })}
    </svg>
  );
};

// ── Main panel ────────────────────────────────────────────────────────────────

const JudgmentAggregationPanel: React.FC = () => {
  const { t } = useTranslation();

  const [scenario,   setScenario]   = useState('legal');
  const [numVoters,  setNumVoters]  = useState(12);
  const [seed,       setSeed]       = useState(42);
  const sim = $api.useMutation('post', '/api/v2/theory/judgment-aggregation');
  const data: JudgData | null = (sim.data as JudgData | undefined) ?? null;
  const loading = sim.isPending;
  const error = sim.isError ? t('judg.error') : null;

  const runSimulation = useCallback(() => {
    sim.mutate({ body: {
      num_voters: numVoters,
      seed,
      scenario,
    } });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scenario, numVoters, seed, t, sim]);

  return (
    <div>
      {/* Controls */}
      <Row className="g-2 mb-3 align-items-end">
        <Col xs={12} md={3}>
          <Form.Label className="small mb-0">{t('judg.scenario')}</Form.Label>
          <Form.Select size="sm" value={scenario} data-testid="scenario-select"
            onChange={(e) => setScenario(e.target.value)}>
            <option value="legal">{t('judg.scenarioLegal')}</option>
            <option value="budget">{t('judg.scenarioBudget')}</option>
            <option value="climate">{t('judg.scenarioClimate')}</option>
          </Form.Select>
        </Col>
        <Col xs={6} md={2}>
          <Form.Label className="small mb-0">{t('judg.numVoters')}</Form.Label>
          <Form.Control type="number" size="sm" min={1} max={100} value={numVoters}
            data-testid="num-voters-input"
            onChange={(e) => setNumVoters(Math.max(1, Math.min(100, Number(e.target.value))))} />
        </Col>
        <Col xs={6} md={2}>
          <Form.Label className="small mb-0">{t('judg.seed')}</Form.Label>
          <Form.Control type="number" size="sm" value={seed}
            data-testid="seed-input"
            onChange={(e) => setSeed(Number(e.target.value))} />
        </Col>
        <Col xs="auto">
          <Button variant="primary" onClick={runSimulation} disabled={loading}
            data-testid="simulate-btn">
            {loading ? <Spinner size="sm" animation="border" /> : t('judg.run')}
          </Button>
        </Col>
      </Row>

      {!data && !loading && !error && (
        <Alert variant="info" role="alert">{t('judg.prompt')}</Alert>
      )}
      {error && <Alert variant="danger">{error}</Alert>}

      {data && (
        <>
          {/* Headline */}
          <div className="d-flex flex-wrap gap-2 mb-3">
            <Badge
              bg={data.collective_coherent ? 'success' : 'danger'}
              data-testid="coherence-badge"
            >
              {data.collective_coherent ? t('judg.coherent') : t('judg.incoherent')}
            </Badge>
            <Badge bg="info" text="dark" data-testid="voter-coherence-badge">
              {t('judg.individualCoherence')}: {Math.round(data.voter_coherence_rate * 100)}%
            </Badge>
            {data.paradox_severity > 0 && (
              <Badge bg="warning" text="dark" data-testid="severity-badge">
                {t('judg.severity')}: {Math.round(data.paradox_severity * 100)}%
              </Badge>
            )}
          </div>

          <Row className="g-3">
            <Col xs={12} md={7}>
              {/* Propositions table */}
              <Table size="sm" hover data-testid="propositions-table">
                <thead>
                  <tr>
                    <th style={{ fontSize: '0.78rem' }}>{t('judg.proposition')}</th>
                    <th style={{ fontSize: '0.78rem' }}>{t('judg.yesPct')}</th>
                    <th style={{ fontSize: '0.78rem' }}>{t('judg.collectiveVote')}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.propositions.map((p) => {
                    const isInco = data.incoherences.some(
                      (inc) => inc.premises.includes(p.id) || inc.conclusion === p.id
                    );
                    return (
                      <tr key={p.id}
                        style={{ background: isInco ? '#fff5f5' : undefined }}>
                        <td style={{ fontSize: '0.78rem' }}>
                          <Badge bg={p.type === 'premise' ? 'secondary' : 'primary'}
                            style={{ fontSize: '0.6rem' }} className="me-1">
                            {p.id}
                          </Badge>
                          {p.text}
                          {isInco && (
                            <Badge bg="danger" className="ms-1" style={{ fontSize: '0.6rem' }}>
                              ⚡
                            </Badge>
                          )}
                        </td>
                        <td style={{ fontSize: '0.78rem' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                            <div style={{
                              width: `${Math.round(p.yes_pct * 60)}px`, height: 8,
                              background: p.collective_vote ? '#198754' : '#dc3545',
                              borderRadius: 4, minWidth: 4,
                            }} />
                            {Math.round(p.yes_pct * 100)}%
                          </div>
                        </td>
                        <td style={{ fontSize: '0.78rem' }}>
                          <span style={{ color: p.collective_vote ? '#198754' : '#dc3545', fontWeight: 700 }}>
                            {p.collective_vote ? '✓ OUI' : '✗ NON'}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </Table>

              {/* Incoherences */}
              {data.incoherences.length > 0 && (
                <Alert variant="danger" style={{ fontSize: '0.8rem' }} data-testid="incoherence-alert">
                  {data.incoherences.map((inc, i) => (
                    <div key={i}>
                      <strong>⚡ {inc.problem}</strong>
                      <div className="text-muted" style={{ fontSize: '0.72rem' }}>
                        Prémisses: {inc.premises.join(', ')} → Conclusion: {inc.conclusion}
                      </div>
                    </div>
                  ))}
                </Alert>
              )}

              {/* Resolution methods */}
              {!data.collective_coherent && (
                <Card className="border-warning mb-2" data-testid="resolution-card">
                  <Card.Header className="py-1" style={{ fontSize: '0.8rem', fontWeight: 700 }}>
                    {t('judg.resolutionTitle')}
                  </Card.Header>
                  <Card.Body className="py-2">
                    <div className="d-flex gap-4" style={{ fontSize: '0.78rem' }}>
                      <div>
                        <div className="text-muted">{t('judg.premiseBased')}</div>
                        {Object.entries(data.resolution_methods.premise_based).map(([k, v]) => (
                          <Badge key={k} bg={v ? 'success' : 'danger'} className="me-1">
                            {k}: {v ? 'OUI' : 'NON'}
                          </Badge>
                        ))}
                      </div>
                      <div>
                        <div className="text-muted">{t('judg.conclusionBased')}</div>
                        <Badge bg="secondary">
                          {t('judg.overridePremise')}
                        </Badge>
                      </div>
                    </div>
                  </Card.Body>
                </Card>
              )}
            </Col>

            <Col xs={12} md={5}>
              {/* Logic tree */}
              <div className="fw-semibold mb-1" style={{ fontSize: '0.85rem' }}>
                {t('judg.logicTreeTitle')}
              </div>
              <div className="border rounded" style={{ background: '#f8f9fa', overflow: 'hidden' }}>
                <LogicTreeSVG data={data} incoherences={data.incoherences} />
              </div>

              {/* Pedagogical note */}
              <Alert variant="secondary" className="mt-2" style={{ fontSize: '0.78rem' }}>
                <strong>{t('judg.noteTitle')}</strong> {data.pedagogical_note}
              </Alert>
            </Col>
          </Row>
        </>
      )}
    </div>
  );
};

export default JudgmentAggregationPanel;
