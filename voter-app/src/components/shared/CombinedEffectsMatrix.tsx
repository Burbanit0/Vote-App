import React, { useCallback, useState } from 'react';
import {
  Alert, Badge, Button, Card, Col, Row, Spinner,
} from 'react-bootstrap';
import {
  Bar, BarChart, CartesianGrid, Cell, LabelList,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { useTranslation } from 'react-i18next';
import { useElection } from '../../stores/useElectionStore';
import {
  fetchCombinedEffects,
  CombinedEffectsResult,
  CombinedEffectsCombination,
} from '../../services/electionApi';
import { useChartTheme } from '../../hooks/useChartTheme';
import LiveBadge from './LiveBadge';
import MetricTooltip from './MetricTooltip';

// ── Colour helpers ────────────────────────────────────────────────────────────

function agreementColor(rate: number): string {
  // green at 1.0, orange at 0.6, red below
  if (rate >= 0.8) return 'rgba(0,122,51,0.15)';
  if (rate >= 0.6) return 'rgba(200,89,10,0.15)';
  return 'rgba(183,28,28,0.15)';
}

function agreementTextColor(rate: number): string {
  if (rate >= 0.8) return '#007A33';
  if (rate >= 0.6) return '#C8590A';
  return '#B71C1C';
}

// ── Matrix cell ───────────────────────────────────────────────────────────────

const MatrixCell: React.FC<{
  combo:    CombinedEffectsCombination | undefined;
  baseWinner: string | null;
  t:        (k: string, opts?: Record<string, unknown>) => string;
}> = ({ combo, baseWinner, t }) => {
  if (!combo) return <td style={{ background: '#f8f9fa' }} />;

  const agreement = combo.inter_method_agreement;
  const changed   = combo.winner_differs_from_base;

  return (
    <td
      style={{
        background:  agreementColor(agreement),
        border:      '1px solid var(--bs-border-color)',
        padding:     '6px 8px',
        textAlign:   'center',
        minWidth:    90,
      }}
    >
      <div style={{ fontWeight: 700, fontSize: '0.85rem', color: changed ? '#B71C1C' : undefined }}>
        {combo.plurality_winner ?? '—'}
        {changed && ' ⚠'}
      </div>
      {combo.condorcet_winner === combo.plurality_winner && combo.condorcet_winner && (
        <Badge bg="success" style={{ fontSize: '0.6rem' }}>✓ C</Badge>
      )}
      <div style={{ fontSize: '0.72rem', color: agreementTextColor(agreement) }}>
        {Math.round(agreement * 100)}%
      </div>
    </td>
  );
};

// ── A) 2×2×2 matrix ──────────────────────────────────────────────────────────

const FactorialMatrix: React.FC<{
  result:    CombinedEffectsResult;
  t:         (k: string, opts?: Record<string, unknown>) => string;
}> = ({ result, t }) => {
  const { combinations, base_winner } = result;

  const find = (blank: boolean, campaign: boolean, info: boolean) =>
    combinations.find(
      (c) => c.blank === blank && c.campaign === campaign && c.information_model === info
    );

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: '0.8rem' }}>
        <thead>
          <tr>
            <th style={{ padding: '6px 8px', background: '#f8f9fa' }} />
            <th colSpan={2} style={{ padding: '6px 8px', textAlign: 'center', background: '#f8f9fa', border: '1px solid var(--bs-border-color)' }}>
              📅 {t('combined.campaignOff')}
            </th>
            <th colSpan={2} style={{ padding: '6px 8px', textAlign: 'center', background: '#f8f9fa', border: '1px solid var(--bs-border-color)' }}>
              📅 {t('combined.campaignOn')}
            </th>
          </tr>
          <tr>
            <th style={{ padding: '4px 8px', background: '#f8f9fa', border: '1px solid var(--bs-border-color)' }} />
            {[false, true, false, true].map((_, i) => (
              <th key={i} style={{ padding: '4px 8px', textAlign: 'center', fontSize: '0.72rem', background: '#f8f9fa', border: '1px solid var(--bs-border-color)' }}>
                📡 {i % 2 === 0 ? t('combined.infoOff') : t('combined.infoOn')}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {[false, true].map((blankOn) => (
            <tr key={String(blankOn)}>
              <th style={{ padding: '6px 8px', background: '#f8f9fa', border: '1px solid var(--bs-border-color)', whiteSpace: 'nowrap' }}>
                □ {blankOn ? t('combined.blankOn') : t('combined.blankOff')}
              </th>
              <MatrixCell combo={find(blankOn, false, false)} baseWinner={base_winner} t={t} />
              <MatrixCell combo={find(blankOn, false, true)}  baseWinner={base_winner} t={t} />
              <MatrixCell combo={find(blankOn, true,  false)} baseWinner={base_winner} t={t} />
              <MatrixCell combo={find(blankOn, true,  true)}  baseWinner={base_winner} t={t} />
            </tr>
          ))}
        </tbody>
      </table>

      {/* Legend */}
      <div className="d-flex gap-3 mt-2 flex-wrap" style={{ fontSize: '0.72rem' }}>
        <span style={{ color: '#007A33' }}>■ ≥ 80% {t('combined.agreement')}</span>
        <span style={{ color: '#C8590A' }}>■ 60–80%</span>
        <span style={{ color: '#B71C1C' }}>■ &lt; 60%</span>
        <span>✓ C = {t('combined.condorcet')}</span>
        <span>⚠ = {t('combined.winnerChanged', { base: base_winner ?? '?' })}</span>
      </div>
    </div>
  );
};

// ── B) Factor contribution bar chart ─────────────────────────────────────────

const FactorBars: React.FC<{
  result: CombinedEffectsResult;
  ct:     ReturnType<typeof useChartTheme>;
  t:      (k: string, opts?: Record<string, unknown>) => string;
}> = ({ result, ct, t }) => {
  const { factor_deltas, most_disruptive_factor } = result;

  const data = [
    { factor: t('combined.factorBlank'),    delta: factor_deltas.blank             ?? 0, key: 'blank' },
    { factor: t('combined.factorCampaign'), delta: factor_deltas.campaign          ?? 0, key: 'campaign' },
    { factor: t('combined.factorInfo'),     delta: factor_deltas.information_model ?? 0, key: 'information_model' },
  ].sort((a, b) => a.delta - b.delta);  // most disruptive (most negative) first

  return (
    <ResponsiveContainer width="100%" height={160}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 60, bottom: 4, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} horizontal={false} />
        <XAxis
          type="number"
          tick={{ fontSize: 10, fill: ct.tickFill }}
          tickFormatter={(v) => `${v > 0 ? '+' : ''}${v.toFixed(1)}%`}
        />
        <YAxis type="category" dataKey="factor" tick={{ fontSize: 10, fill: ct.tickFill }} width={80} />
        <Tooltip
          contentStyle={ct.tooltipStyle}
          formatter={(v: number) => [
            `${v > 0 ? '+' : ''}${v.toFixed(1)}%`,
            t('combined.agreementDelta'),
          ]}
        />
        <Bar dataKey="delta" radius={[0, 4, 4, 0]} isAnimationActive>
          <LabelList
            dataKey="delta"
            position="right"
            style={{ fontSize: 10, fill: ct.tickFill }}
            formatter={(v) => `${(v as number) > 0 ? '+' : ''}${(v as number).toFixed(1)}%`}
          />
          {data.map((entry) => (
            <Cell
              key={entry.key}
              fill={entry.delta < -5 ? '#B71C1C' : entry.delta < 0 ? '#C8590A' : '#007A33'}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
};

// ── C) Synthesis text ─────────────────────────────────────────────────────────

const SynthesisText: React.FC<{
  result: CombinedEffectsResult;
  t:      (k: string, opts?: Record<string, unknown>) => string;
}> = ({ result, t }) => {
  const { combinations, most_disruptive_factor, max_disruption_combination, base_winner } = result;

  const nChanged  = combinations.filter((c) => c.winner_differs_from_base).length;
  const maxCombo  = combinations.find((c) => c.id === max_disruption_combination);
  const maxAgree  = maxCombo ? Math.round(maxCombo.inter_method_agreement * 100) : 0;

  const factorLabel: Record<string, string> = {
    blank:             t('combined.factorBlank'),
    campaign:          t('combined.factorCampaign'),
    information_model: t('combined.factorInfo'),
  };

  return (
    <Alert
      variant={nChanged > 4 ? 'danger' : nChanged > 0 ? 'warning' : 'success'}
      className="mb-0"
      style={{ fontSize: '0.82rem' }}
    >
      {nChanged === 0 ? (
        <span>✓ {t('combined.synthNoChange', { base: base_winner ?? '?' })}</span>
      ) : (
        <span>
          {t('combined.synthIntro', {
            factor:  factorLabel[most_disruptive_factor] ?? most_disruptive_factor,
            changed: nChanged,
            total:   combinations.length,
          })}
          {' '}
          {t('combined.synthMax', {
            combo:   max_disruption_combination,
            agree:   maxAgree,
          })}
        </span>
      )}
    </Alert>
  );
};

// ── Main component ────────────────────────────────────────────────────────────

const CombinedEffectsMatrix: React.FC = () => {
  const { t }       = useTranslation();
  const ct          = useChartTheme();
  const { config }  = useElection();

  const [result,  setResult]  = useState<CombinedEffectsResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState<string | null>(null);

  const run = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setResult(await fetchCombinedEffects({
        candidates:        config.candidates,
        num_voters:        Math.min(config.num_voters, 120),
        ideology:          config.ideology,
        seed:              config.seed,
        blank_vote:        config.blank_vote,
        information_model: config.information_model,
        campaign:          config.campaign,
      }));
    } catch {
      setError(t('combined.error'));
    } finally {
      setLoading(false);
    }
  }, [config, t]);

  return (
    <div>
      {/* Controls */}
      <div className="d-flex align-items-center gap-3 mb-3 flex-wrap">
        <Button variant="primary" size="sm" onClick={run} disabled={loading}>
          {loading
            ? <><Spinner size="sm" className="me-2" />{t('combined.computing')}</>
            : t('combined.compute')}
        </Button>
        <LiveBadge loading={loading && !!result} />
        <span className="text-muted small">{t('combined.hint')}</span>
      </div>

      {error && <Alert variant="danger" className="py-2">{error}</Alert>}

      {!result && !loading && (
        <Alert variant="info" className="py-2">{t('combined.prompt')}</Alert>
      )}

      {result && (
        <Row className="g-3">
          {/* A) Matrix */}
          <Col xs={12}>
            <Card>
              <Card.Header className="py-2">
                <strong style={{ fontSize: '0.85rem' }}>{t('combined.matrixTitle')}</strong>
                <div className="text-muted" style={{ fontSize: '0.75rem' }}>
                  {t('combined.matrixDesc')}
                  {' '}
                  <span style={{ fontWeight: 600 }}>
                    {t('combined.baseWinner', { winner: result.base_winner ?? '?' })}
                  </span>
                </div>
              </Card.Header>
              <Card.Body className="p-2">
                <FactorialMatrix result={result} t={t} />
              </Card.Body>
            </Card>
          </Col>

          {/* B) Factor bars + C) Synthesis */}
          <Col xs={12} lg={6}>
            <Card className="h-100">
              <Card.Header className="py-2">
                <strong style={{ fontSize: '0.85rem' }} className="d-inline-flex align-items-center gap-1">
                  {t('combined.factorTitle')}
                  <MetricTooltip metric="delta_agreement" placement="bottom" />
                </strong>
                <div className="text-muted" style={{ fontSize: '0.75rem' }}>{t('combined.factorDesc')}</div>
              </Card.Header>
              <Card.Body className="p-2">
                <FactorBars result={result} ct={ct} t={t} />
              </Card.Body>
            </Card>
          </Col>

          <Col xs={12} lg={6}>
            <Card className="h-100">
              <Card.Header className="py-2">
                <strong style={{ fontSize: '0.85rem' }}>{t('combined.synthesisTitle')}</strong>
              </Card.Header>
              <Card.Body className="p-2">
                <SynthesisText result={result} t={t} />

                {/* Most / least disruptive badges */}
                <div className="d-flex gap-2 mt-3 flex-wrap" style={{ fontSize: '0.75rem' }}>
                  <Badge bg="danger">
                    ⚠ {t('combined.mostDisruptive')}: {result.most_disruptive_factor}
                  </Badge>
                  <Badge style={{ background: '#007A33' }}>
                    ✓ {t('combined.leastDisruptive')}: {result.least_disruptive_factor}
                  </Badge>
                </div>
              </Card.Body>
            </Card>
          </Col>
        </Row>
      )}
    </div>
  );
};

export default CombinedEffectsMatrix;
