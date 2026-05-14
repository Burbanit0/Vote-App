import React, { useState } from 'react';
import { Badge, Button, Card, Col, Form, Row, Spinner, Table } from 'react-bootstrap';
import { useTranslation } from 'react-i18next';
import { ConstitutionalResult, ScenarioMethodResult } from '../../services/simulationCompareApi';

const COLORS = ['#4e79a7', '#e15759', '#59a14f', '#f28e2b', '#76b7b2', '#edc948'];

interface Props {
  candidateNames: string[];
  result: ConstitutionalResult | null;
  loading: boolean;
  onRun: (duration: 3 | 6, drift: number) => void;
}

function WinnerBadge({ winner, colorMap }: { winner: string | null; colorMap: Record<string, string> }) {
  const { t } = useTranslation();
  if (!winner) return <span className="text-muted">—</span>;
  if (winner === 'Blank') return <Badge bg="warning" text="dark">{t('common.blankBadge')}</Badge>;
  return <Badge style={{ backgroundColor: colorMap[winner] ?? '#999', fontSize: '0.75rem' }}>{winner}</Badge>;
}

const ScenarioBPanel: React.FC<Props> = ({ candidateNames, result, loading, onRun }) => {
  const { t } = useTranslation();
  const [duration, setDuration] = useState<3 | 6>(3);
  const [drift, setDrift] = useState(0.05);

  const colorMap = Object.fromEntries(candidateNames.map((n, i) => [n, COLORS[i % COLORS.length]]));
  const methods = result ? Object.keys(result.before_drift?.methods ?? {}) : [];

  const driftLabel = drift < 0.03 ? t('crisis.drift.weak') : drift < 0.08 ? t('crisis.drift.moderate') : t('crisis.drift.strong');

  return (
    <div>
      <p className="text-muted small mb-3">
        {t('crisis.scenarioBDesc')}
      </p>

      <Row className="g-3 mb-4">
        <Col md={4}>
          <Card>
            <Card.Body>
              <Form.Label className="fw-semibold">{t('crisis.scenarioBDuration')}</Form.Label>
              <div className="d-flex gap-3 mt-2">
                {([3, 6] as const).map((d) => (
                  <Button
                    key={d}
                    variant={duration === d ? 'primary' : 'outline-secondary'}
                    size="sm"
                    onClick={() => setDuration(d)}
                  >
                    {t('crisis.scenarioBMonths', { d })}
                  </Button>
                ))}
              </div>
            </Card.Body>
          </Card>
        </Col>
        <Col md={8}>
          <Card>
            <Card.Body>
              <Form.Label className="fw-semibold">
                <span dangerouslySetInnerHTML={{ __html: t('crisis.scenarioBDrift', { pct: (drift * 100).toFixed(0) }) }} />
                <span className="text-muted ms-2" style={{ fontSize: '0.82rem' }}>{driftLabel}</span>
              </Form.Label>
              <Form.Range min={0} max={0.2} step={0.01} value={drift} onChange={(e) => setDrift(Number(e.target.value))} />
              <small className="text-muted">
                {t('crisis.scenarioBDriftHint', { pct: (drift * 100).toFixed(0) })}
              </small>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      <div className="mb-4">
        <Button variant="success" onClick={() => onRun(duration, drift)} disabled={loading}>
          {loading ? <><Spinner size="sm" className="me-2" />{t('crisis.simulating')}</> : t('crisis.runProvisional')}
        </Button>
      </div>

      {result?.before_drift && result?.after_drift && (
        <>
          <Table bordered size="sm" className="mb-3">
            <thead className="table-light">
              <tr>
                <th style={{ minWidth: 160 }}>{t('common.method')}</th>
                <th className="text-center">{t('crisis.beforeDrift')}</th>
                <th className="text-center">{t('crisis.afterDrift', { duration })}</th>
                <th className="text-center">{t('crisis.blankVoteCol')}</th>
                <th className="text-center">{t('common.changed')}</th>
              </tr>
            </thead>
            <tbody>
              {methods.map((m) => {
                const w1 = (result.before_drift!.methods[m] as ScenarioMethodResult)?.blank_rule_applied?.winner
                        ?? result.before_drift!.methods[m]?.winner ?? null;
                const w2 = (result.after_drift!.methods[m] as ScenarioMethodResult)?.blank_rule_applied?.winner
                        ?? result.after_drift!.methods[m]?.winner ?? null;
                const changed = w1 !== w2;
                const bPct1 = result.before_drift!.blank_pct ?? 0;
                const bPct2 = result.after_drift!.blank_pct ?? 0;
                return (
                  <tr key={m} style={changed ? { backgroundColor: '#e8f4e8' } : undefined}>
                    <td className="ps-2 fw-semibold">{t(`methods.${m}.label`)}</td>
                    <td className="text-center"><WinnerBadge winner={w1} colorMap={colorMap} /></td>
                    <td className="text-center"><WinnerBadge winner={w2} colorMap={colorMap} /></td>
                    <td className="text-center text-muted" style={{ fontSize: '0.82rem' }}>
                      {Math.round(bPct1 * 100)}% → {Math.round(bPct2 * 100)}%
                    </td>
                    <td className="text-center">
                      {changed ? <span style={{ color: '#198754' }}>{t('crisis.changedMark')}</span> : <span className="text-muted">—</span>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </Table>

          <Card className="border-0" style={{ backgroundColor: '#f8f9fa' }}>
            <Card.Body>
              <small className="fw-semibold">{t('crisis.analysis')}</small>
              <p className="mb-0 mt-1 text-muted" style={{ fontSize: '0.85rem' }}>{result.conclusion}</p>
            </Card.Body>
          </Card>
        </>
      )}
    </div>
  );
};

export default ScenarioBPanel;
