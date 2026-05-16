import React, { useCallback, useState } from 'react';
import {
  Alert, Badge, Button, Card, Col, Form, Row, Spinner,
} from 'react-bootstrap';
import {
  Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from 'recharts';
import { useTranslation } from 'react-i18next';
import { useElection } from '../../context/ElectionContext';
import { fetchDivergence, DivergenceResult, DivergenceRunResult } from '../../services/electionApi';
import { useChartTheme } from '../../hooks/useChartTheme';
import LiveBadge from './LiveBadge';

const C = { blue: '#005CAB', orange: '#C8590A', green: '#007A33', red: '#B71C1C', gray: '#6c757d' };

// ── Method comparison column ──────────────────────────────────────────────────

const MethodColumn: React.FC<{
  title:        string;
  run:          DivergenceRunResult;
  changed:      string[];
  isBlank:      boolean;
  t:            (k: string) => string;
}> = ({ title, run, changed, isBlank, t }) => {
  const agreement = Math.round(run.inter_method_agreement * 100);
  const methods   = Object.entries(run.methods).sort(([a], [b]) => a.localeCompare(b));

  return (
    <Card className="h-100">
      <Card.Header className="py-2 text-center">
        <strong style={{ fontSize: '0.85rem' }}>{title}</strong>
      </Card.Header>
      <Card.Body className="p-2">
        {/* Accord badge */}
        <div className="text-center mb-2">
          <Badge
            style={{ fontSize: '0.82rem', background: agreement >= 80 ? C.green : agreement >= 60 ? C.orange : C.red }}
          >
            {t('divergence.agreement')}: {agreement}%
          </Badge>
        </div>

        {/* Condorcet winner */}
        {run.condorcet_winner && (
          <div className="text-center mb-2" style={{ fontSize: '0.78rem', color: C.green }}>
            Condorcet: <strong>{run.condorcet_winner}</strong>
          </div>
        )}

        {/* Blank rate (only for "with blank" column) */}
        {isBlank && run.blank_rate !== undefined && (
          <div className="text-center mb-2" style={{ fontSize: '0.75rem', color: C.gray }}>
            {t('divergence.blankRate')}: {Math.round(run.blank_rate * 100)}%
          </div>
        )}

        {/* Method winner table */}
        <div style={{ fontSize: '0.72rem' }}>
          {methods.map(([method, md]) => {
            const winner = isBlank
              ? (md.winner_after_rule ?? md.winner)
              : md.winner;
            const hasChanged = changed.includes(method);
            return (
              <div
                key={method}
                className="d-flex justify-content-between align-items-center py-1"
                style={{
                  borderBottom: '1px solid var(--bs-border-color)',
                  background: hasChanged ? (isBlank ? 'rgba(183,28,28,0.07)' : 'rgba(0,92,171,0.06)') : undefined,
                }}
              >
                <span className="text-muted" style={{ minWidth: 110 }}>{method}</span>
                <span style={{ fontWeight: 600, color: hasChanged ? (isBlank ? C.red : C.blue) : undefined }}>
                  {winner ?? '—'}
                  {hasChanged && isBlank && ' ⚠'}
                </span>
              </div>
            );
          })}
        </div>
      </Card.Body>
    </Card>
  );
};

// ── Main component ────────────────────────────────────────────────────────────

const BlankVoteDivergencePanel: React.FC = () => {
  const { t }                       = useTranslation();
  const ct                          = useChartTheme();
  const { config }                  = useElection();

  const [rule,    setRule]    = useState<string>(config.blank_vote.rule);
  const [result,  setResult]  = useState<DivergenceResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState<string | null>(null);

  const run = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        candidates: config.candidates,
        num_voters: Math.min(config.num_voters, 300),  // cap for speed
        ideology:   config.ideology,
        seed:       config.seed,
        blank_vote: {
          rule,
          contagion: config.blank_vote.contagion,
        },
      };
      setResult(await fetchDivergence(params));
    } catch {
      setError(t('divergence.error'));
    } finally {
      setLoading(false);
    }
  }, [config, rule, t]);

  // ── Bar chart data (method sensitivity) ──────────────────────────────────
  const barData = result
    ? Object.keys(result.without_blank.methods)
        .sort()
        .map((m) => ({
          method:  m,
          changed: result.methods_changed.includes(m) ? 1 : 0,
        }))
    : [];

  const deltaPositive = (result?.delta_agreement ?? 0) >= 0;
  const deltaPct      = result ? Math.abs(Math.round(result.delta_agreement * 100)) : 0;
  const nChanged      = result?.methods_changed.length ?? 0;
  const totalMethods  = result ? Object.keys(result.without_blank.methods).length : 0;
  const highImpact    = (result?.pct_methods_changed ?? 0) > 0.30;

  return (
    <div>
      {/* Controls */}
      <div className="d-flex align-items-end gap-3 mb-3 flex-wrap">
        <div>
          <Form.Label className="small mb-1">{t('divergence.rule')}</Form.Label>
          <Form.Select size="sm" value={rule} style={{ width: 190 }}
            onChange={(e) => { setRule(e.target.value); setResult(null); }}>
            <option value="symbolic">{t('divergence.ruleSymbolic')}</option>
            <option value="competitive">{t('divergence.ruleCompetitive')}</option>
            <option value="threshold_30">{t('divergence.ruleThreshold')}</option>
          </Form.Select>
        </div>

        <Button variant="primary" size="sm" onClick={run} disabled={loading}>
          {loading
            ? <><Spinner size="sm" className="me-2" />{t('divergence.computing')}</>
            : t('divergence.compute')}
        </Button>
        <LiveBadge loading={loading && !!result} />
      </div>

      {error && <Alert variant="danger" className="py-2">{error}</Alert>}

      {!result && !loading && (
        <Alert variant="info" className="py-2">{t('divergence.prompt')}</Alert>
      )}

      {result && (
        <>
          {/* Delta badge */}
          <div className="d-flex justify-content-center mb-3">
            <Badge
              style={{
                fontSize: '0.95rem', padding: '8px 16px',
                background: deltaPositive ? C.green : (deltaPct >= 5 ? C.red : C.gray),
              }}
            >
              Δ {t('divergence.agreement')}{' '}
              {deltaPositive ? '+' : '−'}{deltaPct}%
              {' '}
              {deltaPositive
                ? `(${t('divergence.moreAgreement')})`
                : deltaPct >= 5 ? `(${t('divergence.moreDivergence')})` : ''}
            </Badge>
          </div>

          {/* Two-column comparison */}
          <Row className="g-3 mb-4">
            <Col xs={12} md={6}>
              <MethodColumn
                title={t('divergence.withoutBlank')}
                run={result.without_blank}
                changed={result.methods_changed}
                isBlank={false}
                t={t}
              />
            </Col>

            {/* Arrow separator (visible on md+) */}
            <Col xs={12} md={6}>
              <MethodColumn
                title={t('divergence.withBlank', { rule })}
                run={result.with_blank}
                changed={result.methods_changed}
                isBlank={true}
                t={t}
              />
            </Col>
          </Row>

          {/* Sensitivity bar chart */}
          {barData.length > 0 && (
            <Card className="mb-3">
              <Card.Header className="py-2">
                <strong style={{ fontSize: '0.85rem' }}>{t('divergence.sensitivityChart')}</strong>
                <span className="text-muted ms-2" style={{ fontSize: '0.75rem' }}>
                  — {nChanged}/{totalMethods} {t('divergence.methodsChanged')}
                </span>
              </Card.Header>
              <Card.Body className="p-2">
                <ResponsiveContainer width="100%" height={120}>
                  <BarChart data={barData} margin={{ top: 4, right: 16, bottom: 40, left: 4 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} vertical={false} />
                    <XAxis
                      dataKey="method"
                      tick={{ fontSize: 9, fill: ct.tickFill }}
                      angle={-40}
                      textAnchor="end"
                      interval={0}
                    />
                    <YAxis hide domain={[0, 1]} />
                    <Tooltip
                      contentStyle={ct.tooltipStyle}
                      formatter={(v: number) => [v === 1 ? t('divergence.changed') : t('divergence.stable'), '']}
                    />
                    <Bar dataKey="changed" radius={[3, 3, 0, 0]} isAnimationActive>
                      {barData.map((entry) => (
                        <Cell
                          key={entry.method}
                          fill={entry.changed === 1 ? C.red : C.green}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
                <div className="d-flex gap-3 mt-1" style={{ fontSize: '0.72rem' }}>
                  <span className="d-flex align-items-center gap-1">
                    <span style={{ width: 10, height: 10, borderRadius: 2, background: C.green, display: 'inline-block' }} />
                    {t('divergence.stable')}
                  </span>
                  <span className="d-flex align-items-center gap-1">
                    <span style={{ width: 10, height: 10, borderRadius: 2, background: C.red, display: 'inline-block' }} />
                    {t('divergence.changed')}
                  </span>
                </div>
              </Card.Body>
            </Card>
          )}

          {/* Pedagogical message */}
          {highImpact && (
            <Alert variant="warning" className="py-2" style={{ fontSize: '0.82rem' }}>
              ⚠️ {t('divergence.highImpactMessage', {
                pct:     Math.round(result.pct_methods_changed * 100),
                methods: result.methods_changed.slice(0, 3).join(', '),
              })}
            </Alert>
          )}
          {!highImpact && nChanged === 0 && (
            <Alert variant="success" className="py-2" style={{ fontSize: '0.82rem' }}>
              ✓ {t('divergence.noImpactMessage')}
            </Alert>
          )}
        </>
      )}
    </div>
  );
};

export default BlankVoteDivergencePanel;
