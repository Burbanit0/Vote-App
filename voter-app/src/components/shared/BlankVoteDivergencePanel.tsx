import React, { useCallback, useState } from 'react';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { Select } from '@/components/ui/form-controls';
import { Col, Row } from '@/components/ui/grid';
import { Spinner } from '@/components/ui/spinner';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useTranslation } from 'react-i18next';
import { useElection } from '../../stores/useElectionStore';
import MetricTooltip from './MetricTooltip';
import { fetchDivergence, DivergenceResult, DivergenceRunResult } from '../../services/electionApi';
import { useChartTheme } from '../../hooks/useChartTheme';
import LiveBadge from './LiveBadge';
import PinToCentralButton from './PinToCentralButton';

import { numericTooltipFormatter } from '@/lib/rechartsFormatters';

const C = { blue: '#005CAB', orange: '#C8590A', green: '#007A33', red: '#B71C1C', gray: '#6c757d' };

// ── Method comparison column ──────────────────────────────────────────────────

const MethodColumn: React.FC<{
  title: string;
  run: DivergenceRunResult;
  changed: string[];
  isBlank: boolean;
  t: (k: string) => string;
}> = ({ title, run, changed, isBlank, t }) => {
  const agreement = Math.round(run.inter_method_agreement * 100);
  const methods = Object.entries(run.methods).sort(([a], [b]) => a.localeCompare(b));

  return (
    <Card className="h-full">
      <CardHeader className="block space-y-0 border-b border-border px-4 py-2 py-2 text-center">
        <strong style={{ fontSize: '0.85rem' }}>{title}</strong>
      </CardHeader>
      <CardBody className="p-2">
        {/* Accord badge */}
        <div className="text-center mb-2">
          <Badge
            className="inline-flex items-center gap-1"
            style={{
              fontSize: '0.82rem',
              background: agreement >= 80 ? C.green : agreement >= 60 ? C.orange : C.red,
            }}
          >
            {t('divergence.agreement')}: {agreement}%
            <MetricTooltip metric="method_agreement" placement="bottom" />
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
            const winner = isBlank ? (md.winner_after_rule ?? md.winner) : md.winner;
            const hasChanged = changed.includes(method);
            return (
              <div
                key={method}
                className="flex justify-between items-center py-1"
                style={{
                  borderBottom: '1px solid var(--bs-border-color)',
                  background: hasChanged
                    ? isBlank
                      ? 'rgba(183,28,28,0.07)'
                      : 'rgba(0,92,171,0.06)'
                    : undefined,
                }}
              >
                <span className="text-muted-foreground" style={{ minWidth: 110 }}>
                  {method}
                </span>
                <span
                  style={{
                    fontWeight: 600,
                    color: hasChanged ? (isBlank ? C.red : C.blue) : undefined,
                  }}
                >
                  {winner ?? '—'}
                  {hasChanged && isBlank && ' ⚠'}
                </span>
              </div>
            );
          })}
        </div>
      </CardBody>
    </Card>
  );
};

// ── Main component ────────────────────────────────────────────────────────────

const BlankVoteDivergencePanel: React.FC = () => {
  const { t } = useTranslation();
  const ct = useChartTheme();
  const { config } = useElection();

  const [rule, setRule] = useState<string>(config.blank_vote.rule);
  const [result, setResult] = useState<DivergenceResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        candidates: config.candidates,
        num_voters: Math.min(config.num_voters, 300), // cap for speed
        ideology: config.ideology,
        seed: config.seed,
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
          method: m,
          changed: result.methods_changed.includes(m) ? 1 : 0,
        }))
    : [];

  const deltaPositive = (result?.delta_agreement ?? 0) >= 0;
  const deltaPct = result ? Math.abs(Math.round(result.delta_agreement * 100)) : 0;
  const nChanged = result?.methods_changed.length ?? 0;
  const totalMethods = result ? Object.keys(result.without_blank.methods).length : 0;
  const highImpact = (result?.pct_methods_changed ?? 0) > 0.3;

  return (
    <div>
      {/* Controls */}
      <div className="flex items-end gap-3 mb-3 flex-wrap">
        <div>
          <label className="mb-1 inline-block text-sm mb-1">{t('divergence.rule')}</label>
          <Select
            size="sm"
            value={rule}
            style={{ width: 190 }}
            onChange={(e) => {
              setRule(e.target.value);
              setResult(null);
            }}
          >
            <option value="symbolic">{t('divergence.ruleSymbolic')}</option>
            <option value="competitive">{t('divergence.ruleCompetitive')}</option>
            <option value="threshold_30">{t('divergence.ruleThreshold')}</option>
          </Select>
        </div>

        <Button variant="primary" size="sm" onClick={run} disabled={loading}>
          {loading ? (
            <>
              <Spinner size="sm" className="me-2" />
              {t('divergence.computing')}
            </>
          ) : (
            t('divergence.compute')
          )}
        </Button>
        <LiveBadge loading={loading && !!result} />
        {result &&
          (() => {
            // Build winners-by-method from with_blank run, count changes vs without_blank
            const winnersByMethod: Record<string, string | null> = {};
            let changedCount = 0;
            Object.entries(result.with_blank.methods).forEach(([m, md]) => {
              const wb = md.winner_after_rule ?? md.winner;
              winnersByMethod[m] = wb;
              const baseline = result.without_blank.methods[m]?.winner;
              if (wb !== baseline) changedCount += 1;
            });
            return (
              <PinToCentralButton
                type="blank-divergence"
                icon="⬜"
                label={`${t('divergence.compute')} — ${rule}`}
                summary={
                  changedCount > 0
                    ? `${changedCount}/${Object.keys(winnersByMethod).length} ${t('lab.methodsChanged')}`
                    : t('lab.winnerStable')
                }
                methodsChanged={changedCount}
                winnersByMethod={winnersByMethod}
              />
            );
          })()}
      </div>

      {error && (
        <Alert variant="danger" className="py-2">
          {error}
        </Alert>
      )}

      {!result && !loading && (
        <Alert variant="info" className="py-2">
          {t('divergence.prompt')}
        </Alert>
      )}

      {result && (
        <>
          {/* Delta badge */}
          <div className="flex justify-center mb-3">
            <Badge
              className="inline-flex items-center gap-1"
              style={{
                fontSize: '0.95rem',
                padding: '8px 16px',
                background: deltaPositive ? C.green : deltaPct >= 5 ? C.red : C.gray,
              }}
            >
              Δ {t('divergence.agreement')} {deltaPositive ? '+' : '−'}
              {deltaPct}% <MetricTooltip metric="delta_agreement" placement="bottom" />
              {deltaPositive
                ? `(${t('divergence.moreAgreement')})`
                : deltaPct >= 5
                  ? `(${t('divergence.moreDivergence')})`
                  : ''}
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
              <CardHeader className="block space-y-0 border-b border-border px-4 py-2 py-2">
                <strong style={{ fontSize: '0.85rem' }}>{t('divergence.sensitivityChart')}</strong>
                <span className="text-muted-foreground ms-2" style={{ fontSize: '0.75rem' }}>
                  — {nChanged}/{totalMethods} {t('divergence.methodsChanged')}
                </span>
              </CardHeader>
              <CardBody className="p-2">
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
                      formatter={numericTooltipFormatter((v: number) => [
                        v === 1 ? t('divergence.changed') : t('divergence.stable'),
                        '',
                      ])}
                    />
                    <Bar dataKey="changed" radius={[3, 3, 0, 0]} isAnimationActive>
                      {barData.map((entry) => (
                        <Cell key={entry.method} fill={entry.changed === 1 ? C.red : C.green} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
                <div className="flex gap-3 mt-1" style={{ fontSize: '0.72rem' }}>
                  <span className="flex items-center gap-1">
                    <span
                      style={{
                        width: 10,
                        height: 10,
                        borderRadius: 2,
                        background: C.green,
                        display: 'inline-block',
                      }}
                    />
                    {t('divergence.stable')}
                  </span>
                  <span className="flex items-center gap-1">
                    <span
                      style={{
                        width: 10,
                        height: 10,
                        borderRadius: 2,
                        background: C.red,
                        display: 'inline-block',
                      }}
                    />
                    {t('divergence.changed')}
                  </span>
                </div>
              </CardBody>
            </Card>
          )}

          {/* Pedagogical message */}
          {highImpact && (
            <Alert variant="warning" className="py-2" style={{ fontSize: '0.82rem' }}>
              ⚠️{' '}
              {t('divergence.highImpactMessage', {
                pct: Math.round(result.pct_methods_changed * 100),
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
