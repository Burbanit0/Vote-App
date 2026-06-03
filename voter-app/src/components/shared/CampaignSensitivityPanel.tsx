import React, { useCallback, useMemo, useState } from 'react';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { Check, Range } from '@/components/ui/form-controls';
import { Col, Row } from '@/components/ui/grid';
import { Spinner } from '@/components/ui/spinner';
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell,
  Legend, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { useTranslation } from 'react-i18next';
import { useElection } from '../../stores/useElectionStore';
import {
  fetchCampaignSensitivity,
  CampaignSensitivityResult,
} from '../../services/electionApi';
import { useChartTheme } from '../../hooks/useChartTheme';
import LiveBadge from './LiveBadge';
import PinToCentralButton from './PinToCentralButton';
import CampaignSwimlane from './CampaignSwimlane';

// ── Constants ─────────────────────────────────────────────────────────────────

const SNAPSHOT_DAYS = [0, 7, 14, 21, 28, 'final'] as const;
const METHOD_COLORS = [
  '#005CAB', '#C8590A', '#007A33', '#7B2D8B', '#9C3A00',
  '#005f73', '#ae2012', '#94d2bd', '#e9d8a6', '#ee9b00',
  '#ca6702', '#bb3e03', '#0a9396', '#001219',
];

// ── Helpers ───────────────────────────────────────────────────────────────────

function stabilityColor(score: number): string {
  if (score >= 0.8) return '#007A33';
  if (score >= 0.5) return '#C8590A';
  return '#B71C1C';
}

// ── Sub-charts ────────────────────────────────────────────────────────────────

/**
 * A) Timeline of winners per method.
 * Maps candidates → numeric Y-values so Recharts LineChart can draw step lines.
 */
const WinnerTimeline: React.FC<{
  result: CampaignSensitivityResult;
  ct:     ReturnType<typeof useChartTheme>;
  t:      (k: string, opts?: Record<string, unknown>) => string;
}> = ({ result, ct, t }) => {
  const { snapshots, method_stability } = result;

  // Sort methods: most stable first, show top 5
  const top5 = useMemo(
    () =>
      Object.entries(method_stability)
        .sort(([, a], [, b]) => b.stability_score - a.stability_score)
        .slice(0, 5)
        .map(([m]) => m),
    [method_stability]
  );

  // Collect all unique candidates (for Y-axis mapping)
  const allCandidates = useMemo(() => {
    const names = new Set<string>();
    snapshots.forEach((s) =>
      Object.values(s.methods).forEach((md) => { if (md.winner) names.add(md.winner); })
    );
    return [...names].sort();
  }, [snapshots]);

  const candIndex = useMemo(
    () => Object.fromEntries(allCandidates.map((c, i) => [c, i])),
    [allCandidates]
  );

  const data = snapshots.map((s) => {
    const row: Record<string, number | string> = { day: s.day };
    top5.forEach((m) => {
      const winner = s.methods[m]?.winner ?? null;
      row[m] = winner != null ? candIndex[winner] ?? 0 : -1;
    });
    return row;
  });

  if (allCandidates.length === 0) return null;

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} />
        <XAxis
          dataKey="day"
          tick={{ fontSize: 10, fill: ct.tickFill }}
          label={{ value: t('campaign.day'), position: 'insideBottomRight', offset: -4, fontSize: 10, fill: ct.tickFill }}
        />
        <YAxis
          tick={{ fontSize: 10, fill: ct.tickFill }}
          tickFormatter={(v: number) => allCandidates[v] ?? ''}
          domain={[0, allCandidates.length - 1]}
          ticks={allCandidates.map((_, i) => i)}
        />
        <Tooltip
          contentStyle={ct.tooltipStyle}
          formatter={(v: number, name: string) => [allCandidates[v] ?? '—', name]}
          labelFormatter={(l) => `${t('campaign.day')} ${l}`}
        />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        {top5.map((m, idx) => (
          <Bar
            key={m}
            dataKey={m}
            fill={METHOD_COLORS[idx % METHOD_COLORS.length]}
            isAnimationActive={false}
            barSize={12}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
};

/**
 * B) Horizontal BarChart of stability scores, sorted descending.
 */
const StabilityChart: React.FC<{
  result: CampaignSensitivityResult;
  ct:     ReturnType<typeof useChartTheme>;
  t:      (k: string, opts?: Record<string, unknown>) => string;
}> = ({ result, ct, t }) => {
  const { method_stability, most_stable_method, least_stable_method } = result;

  const data = useMemo(
    () =>
      Object.entries(method_stability)
        .map(([method, s]) => ({ method, score: s.stability_score, changes: s.winner_changes }))
        .sort((a, b) => b.score - a.score),
    [method_stability]
  );

  const mostStable  = method_stability[most_stable_method  ?? ''];
  const leastStable = method_stability[least_stable_method ?? ''];

  return (
    <div>
      {/* Pedagogical messages */}
      {most_stable_method && mostStable && mostStable.winner_changes === 0 && (
        <Alert variant="success" className="py-2 mb-2" style={{ fontSize: '0.8rem' }}>
          ✓ {t('campaign.mostStableMsg', {
            method: most_stable_method,
          })}
        </Alert>
      )}
      {least_stable_method && leastStable && leastStable.winner_changes > 0 && (
        <Alert variant="warning" className="py-2 mb-2" style={{ fontSize: '0.8rem' }}>
          ⚠ {t('campaign.leastStableMsg', {
            method:  least_stable_method,
            changes: leastStable.winner_changes,
          })}
        </Alert>
      )}

      <ResponsiveContainer width="100%" height={Math.max(160, data.length * 24)}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 4, right: 60, bottom: 4, left: 8 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} horizontal={false} />
          <XAxis type="number" domain={[0, 1]} tick={{ fontSize: 10, fill: ct.tickFill }} tickFormatter={(v) => `${Math.round(v * 100)}%`} />
          <YAxis type="category" dataKey="method" tick={{ fontSize: 10, fill: ct.tickFill }} width={110} />
          <Tooltip
            contentStyle={ct.tooltipStyle}
            formatter={(v: number) => [`${Math.round(v * 100)}%`, t('campaign.stabilityScore')]}
          />
          <Bar dataKey="score" radius={[0, 4, 4, 0]} isAnimationActive>
            {data.map((entry) => (
              <Cell key={entry.method} fill={stabilityColor(entry.score)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Most / Least stable badges */}
      <div className="d-flex gap-2 mt-2 flex-wrap" style={{ fontSize: '0.75rem' }}>
        {most_stable_method && (
          <Badge style={{ background: '#007A33' }}>
            ✓ {t('campaign.mostStable')}: {most_stable_method}
          </Badge>
        )}
        {least_stable_method && least_stable_method !== most_stable_method && (
          <Badge variant="danger">
            ⚠ {t('campaign.leastStable')}: {least_stable_method}
          </Badge>
        )}
      </div>
    </div>
  );
};

/**
 * C) AreaChart of inter-method agreement over time.
 */
const AgreementTimeline: React.FC<{
  result: CampaignSensitivityResult;
  ct:     ReturnType<typeof useChartTheme>;
  t:      (k: string, opts?: Record<string, unknown>) => string;
}> = ({ result, ct, t }) => {
  const data = result.snapshots.map((s) => ({
    day:  s.day,
    rate: Math.round(s.inter_method_agreement * 100),
  }));

  return (
    <ResponsiveContainer width="100%" height={160}>
      <AreaChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
        <defs>
          <linearGradient id="agreeGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor="#005CAB" stopOpacity={0.25} />
            <stop offset="95%" stopColor="#005CAB" stopOpacity={0.04} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} />
        <XAxis
          dataKey="day"
          tick={{ fontSize: 10, fill: ct.tickFill }}
          label={{ value: t('campaign.day'), position: 'insideBottomRight', offset: -4, fontSize: 10, fill: ct.tickFill }}
        />
        <YAxis tick={{ fontSize: 10, fill: ct.tickFill }} domain={[0, 100]} unit="%" />
        <Tooltip
          contentStyle={ct.tooltipStyle}
          formatter={(v: number) => [`${v}%`, t('divergence.agreement')]}
          labelFormatter={(l) => `${t('campaign.day')} ${l}`}
        />
        <Area
          type="monotone"
          dataKey="rate"
          stroke="#005CAB"
          fill="url(#agreeGrad)"
          strokeWidth={2}
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
};

// ── Main component ────────────────────────────────────────────────────────────

const CampaignSensitivityPanel: React.FC = () => {
  const { t }          = useTranslation();
  const ct             = useChartTheme();
  const { config }     = useElection();

  const [pollingEffect, setPollingEffect] = useState(config.campaign.polling_effect);
  const [numDays,       setNumDays]       = useState(config.campaign.num_days);
  const [withContagion, setWithContagion] = useState(config.blank_vote.contagion.enabled);
  const [result,        setResult]        = useState<CampaignSensitivityResult | null>(null);
  const [loading,       setLoading]       = useState(false);
  const [error,         setError]         = useState<string | null>(null);

  const run = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        candidates:    config.candidates,
        num_voters:    Math.min(config.num_voters, 150),
        ideology:      config.ideology,
        seed:          config.seed,
        campaign:      { num_days: numDays, polling_effect: pollingEffect },
        blank_vote: {
          enabled:   withContagion,
          rule:      config.blank_vote.rule,
          contagion: { ...config.blank_vote.contagion, enabled: withContagion },
        },
        snapshot_days: SNAPSHOT_DAYS as unknown as (number | 'final')[],
      };
      setResult(await fetchCampaignSensitivity(params));
    } catch {
      setError(t('campaign.error'));
    } finally {
      setLoading(false);
    }
  }, [config, numDays, pollingEffect, withContagion, t]);

  return (
    <div>
      {/* Controls */}
      <Row className="g-3 align-items-end mb-3">
        <Col md={3}>
          <label className="mb-1 inline-block small mb-0">
            {t('campaign.pollingEffect')}: <strong>{pollingEffect.toFixed(2)}</strong>
          </label>
          <Range min={0} max={1} step={0.05} value={pollingEffect}
            onChange={(e) => { setPollingEffect(Number(e.target.value)); setResult(null); }} />
        </Col>
        <Col md={3}>
          <label className="mb-1 inline-block small mb-0">
            {t('campaign.numDays')}: <strong>{numDays}</strong>
          </label>
          <Range min={7} max={60} step={1} value={numDays}
            onChange={(e) => { setNumDays(Number(e.target.value)); setResult(null); }} />
        </Col>
        <Col md={3} className="d-flex align-items-end">
          <Check
            type="switch"
            id="contagion-toggle"
            label={<span className="small">{t('campaign.withContagion')}</span>}
            checked={withContagion}
            onChange={(e) => { setWithContagion(e.target.checked); setResult(null); }}
          />
        </Col>
        <Col md={3}>
          <Button variant="primary" size="sm" className="w-100" onClick={run} disabled={loading}>
            {loading
              ? <><Spinner size="sm" className="me-2" />{t('campaign.computing')}</>
              : t('campaign.compute')}
          </Button>
          <LiveBadge loading={loading && !!result} className="mt-1" />
        </Col>
        {result && (
          <Col md="auto">
            <PinToCentralButton
              type="campaign-sensitivity"
              icon="📈"
              label={`${t('campaign.compute')} — ${numDays}j`}
              summary={(() => {
                // Count methods that changed final winner under campaign
                const winnersByMethod: Record<string, string | null> = {};
                let changed = 0;
                Object.entries(result.method_stability).forEach(([m, st]) => {
                  winnersByMethod[m] = st.final_winner;
                  if (st.winner_changes > 0) changed += 1;
                });
                return changed > 0
                  ? `${changed}/${Object.keys(result.method_stability).length} ${t('lab.methodsChanged')}`
                  : t('lab.winnerStable');
              })()}
              methodsChanged={Object.values(result.method_stability).filter(s => s.winner_changes > 0).length}
              winnersByMethod={Object.fromEntries(
                Object.entries(result.method_stability).map(([m, st]) => [m, st.final_winner])
              )}
            />
          </Col>
        )}
      </Row>

      {error && <Alert variant="danger" className="py-2">{error}</Alert>}

      {!result && !loading && (
        <Alert variant="info" className="py-2">{t('campaign.prompt')}</Alert>
      )}

      {result && (
        <Row className="g-3">
          {/* A) Swimlane — winner timeline */}
          <Col xs={12}>
            <Card>
              <CardHeader className="block space-y-0 border-b border-border px-4 py-2 py-2">
                <strong style={{ fontSize: '0.85rem' }}>{t('campaign.swimlaneTitle')}</strong>
                <div className="text-muted" style={{ fontSize: '0.75rem' }}>{t('campaign.swimlaneDesc')}</div>
              </CardHeader>
              <CardBody className="p-2">
                <CampaignSwimlane
                  snapshots={result.snapshots}
                  methodStability={result.method_stability}
                  candidates={[...new Set(result.snapshots.flatMap((s) =>
                    Object.values(s.methods).map((m) => m.winner).filter((w): w is string => !!w)
                  ))]}
                />
              </CardBody>
            </Card>
          </Col>

          {/* B) Stability + C) Agreement side by side */}
          <Col xs={12} lg={7}>
            <Card className="h-100">
              <CardHeader className="block space-y-0 border-b border-border px-4 py-2 py-2">
                <strong style={{ fontSize: '0.85rem' }}>{t('campaign.stabilityTitle')}</strong>
                <div className="text-muted" style={{ fontSize: '0.75rem' }}>{t('campaign.stabilityDesc')}</div>
              </CardHeader>
              <CardBody className="p-2">
                <StabilityChart result={result} ct={ct} t={t} />
              </CardBody>
            </Card>
          </Col>

          <Col xs={12} lg={5}>
            <Card className="h-100">
              <CardHeader className="block space-y-0 border-b border-border px-4 py-2 py-2">
                <strong style={{ fontSize: '0.85rem' }}>{t('campaign.agreementTitle')}</strong>
                <div className="text-muted" style={{ fontSize: '0.75rem' }}>{t('campaign.agreementDesc')}</div>
              </CardHeader>
              <CardBody className="p-2">
                <AgreementTimeline result={result} ct={ct} t={t} />
              </CardBody>
            </Card>
          </Col>
        </Row>
      )}
    </div>
  );
};

export default CampaignSensitivityPanel;
