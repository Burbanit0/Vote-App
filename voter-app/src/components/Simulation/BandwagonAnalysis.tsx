import React, { useMemo, useState } from 'react';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { Range } from '@/components/ui/form-controls';
import { Col, Row } from '@/components/ui/grid';
import { Spinner } from '@/components/ui/spinner';
import { Table } from '@/components/ui/table';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Trans, useTranslation } from 'react-i18next';
import { BandwagonResult } from '../../types';
import { getBandwagonAnalysis, BandwagonParams } from '../../services/simulationCompareApi';
import SkeletonCard from '../shared/SkeletonCard';
import { useChartTheme } from '../../hooks/useChartTheme';

import { numericTooltipFormatter } from '@/lib/rechartsFormatters';

// ── Constants ──────────────────────────────────────────────────────────────

const CANDIDATE_COLORS = [
  '#4e79a7',
  '#f28e2b',
  '#e15759',
  '#76b7b2',
  '#59a14f',
  '#edc948',
  '#b07aa1',
  '#ff9da7',
];

const METHOD_COLORS = [
  '#e15759',
  '#4e79a7',
  '#59a14f',
  '#f28e2b',
  '#76b7b2',
  '#edc948',
  '#b07aa1',
  '#9c755f',
  '#bab0ac',
  '#86bcb6',
  '#499894',
];

// ── Component ──────────────────────────────────────────────────────────────

interface Props {
  baseParams: CompareBaseParams;
}

interface CompareBaseParams {
  num_voters?: number;
  candidates?: string[];
  ideology_distribution?: string;
}

const BandwagonAnalysis: React.FC<Props> = ({ baseParams }) => {
  const { t } = useTranslation();
  const ct = useChartTheme();
  const [numRounds, setNumRounds] = useState(6);
  const [influenceStrength, setInfluenceStrength] = useState(0.3);
  const [result, setResult] = useState<BandwagonResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const METHOD_LABELS: Record<string, string> = useMemo(
    () => ({
      plurality: t('methods.plurality.label'),
      two_round: t('methods.two_round.label'),
      borda: t('methods.borda.label'),
      approval: t('methods.approval.label'),
      irv: t('methods.irv.label'),
      coombs: t('methods.coombs.label'),
      bucklin: t('methods.bucklin.label'),
      minimax: t('methods.minimax.label'),
      schulze: t('methods.schulze.label'),
      condorcet: t('methods.condorcet.label'),
      positional_score: t('methods.positional_score.label'),
    }),
    [t]
  );

  function amplificationLabel(rate: number): {
    label: string;
    variant: 'success' | 'warning' | 'danger';
  } {
    if (rate <= 0.1) return { label: t('simulation.bandwagonResists'), variant: 'success' };
    if (rate <= 0.3) return { label: t('simulation.bandwagonAmplifiesSlight'), variant: 'warning' };
    return { label: t('simulation.bandwagonAmplifiesStrong'), variant: 'danger' };
  }

  const runSimulation = async () => {
    setLoading(true);
    setError(null);
    try {
      const params: BandwagonParams = {
        ...baseParams,
        num_rounds: numRounds,
        influence_strength: influenceStrength,
      };
      const data = await getBandwagonAnalysis(params);
      setResult(data);
    } catch {
      setError(t('simulation.errBandwagon'));
    } finally {
      setLoading(false);
    }
  };

  // ── Derived chart data ──────────────────────────────────────────────────

  const candidateNames = result ? Object.keys(result.rounds[0]?.poll_standings ?? {}) : [];

  const methodNames = result ? Object.keys(result.rounds[0]?.methods ?? {}) : [];

  const pollChartData =
    result?.rounds.map((r) => ({
      round: `R${r.round}`,
      ...r.poll_standings,
      polarization: r.voter_lean_distribution.polarization_index,
    })) ?? [];

  const regretChartData =
    result?.rounds.map((r) => ({
      round: `R${r.round}`,
      ...Object.fromEntries(
        Object.entries(r.methods).map(([m, d]) => [METHOD_LABELS[m] ?? m, d.bayesian_regret])
      ),
    })) ?? [];

  // Breakpoints: rounds where the poll leader changes
  const pollBreakpoints: { round: string; to: string }[] = result
    ? result.rounds.slice(1).reduce<{ round: string; to: string }[]>((acc, r, i) => {
        const prev = result.rounds[i].poll_standings;
        const curr = r.poll_standings;
        const prevLeader = Object.entries(prev).sort((a, b) => b[1] - a[1])[0]?.[0];
        const currLeader = Object.entries(curr).sort((a, b) => b[1] - a[1])[0]?.[0];
        if (prevLeader !== currLeader && currLeader)
          acc.push({ round: `R${r.round}`, to: currLeader });
        return acc;
      }, [])
    : [];

  const influenceLabel =
    influenceStrength < 0.2
      ? t('simulation.influence.weak')
      : influenceStrength < 0.5
        ? t('simulation.influence.moderate')
        : t('simulation.influence.strong');

  // ── Render ─────────────────────────────────────────────────────────────

  return (
    <div>
      {/* Controls */}
      <Card className="mb-4">
        <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
          <strong>{t('simulation.bandwagonConfig')}</strong>
        </CardHeader>
        <CardBody>
          <Row className="g-3 items-end">
            <Col md={3}>
              <label className="mb-1 inline-block text-sm mb-1">
                {t('simulation.rounds')} : <strong>{numRounds}</strong>
              </label>
              <Range
                min={2}
                max={12}
                value={numRounds}
                onChange={(e) => setNumRounds(Number(e.target.value))}
              />
            </Col>
            <Col md={4}>
              <label className="mb-1 inline-block text-sm mb-1">
                {t('simulation.influenceStrength')} :{' '}
                <strong>{influenceStrength.toFixed(2)}</strong>
                <span className="text-muted-foreground ms-1">({influenceLabel})</span>
              </label>
              <Range
                min={0}
                max={1}
                step={0.05}
                value={influenceStrength}
                onChange={(e) => setInfluenceStrength(Number(e.target.value))}
              />
            </Col>
            <Col md={2}>
              <Button
                variant="primary"
                className="w-full"
                onClick={runSimulation}
                disabled={loading}
              >
                {loading ? (
                  <>
                    <Spinner size="sm" className="me-2" />
                    {t('simulation.runningEllipsis')}
                  </>
                ) : (
                  t('common.run')
                )}
              </Button>
            </Col>
          </Row>
          <p className="text-muted-foreground text-sm mt-2 mb-0">{t('simulation.bandwagonInfo')}</p>
        </CardBody>
      </Card>

      {error && <Alert variant="danger">{error}</Alert>}

      {loading && (
        <Row className="g-3 mb-2">
          {[240, 300, 180].map((h, i) => (
            <Col key={i} md={4}>
              <SkeletonCard height={h} />
            </Col>
          ))}
        </Row>
      )}

      {!result && !loading && (
        <Alert variant="info">
          <Trans i18nKey="simulation.bandwagonPrompt" />
        </Alert>
      )}

      {result && (
        <>
          {/* Convergence info */}
          {result.convergence_round !== null ? (
            <Alert variant="success" className="py-2 mb-4">
              <Trans
                i18nKey="simulation.bandwagonConverged"
                values={{ round: result.convergence_round }}
              />
            </Alert>
          ) : (
            <Alert variant="warning" className="py-2 mb-4">
              {t('simulation.bandwagonNoConvergence', { numRounds: result.num_rounds })}
            </Alert>
          )}

          {/* Chart 1: Poll standings evolution */}
          <Card className="mb-4">
            <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
              <strong>{t('simulation.pollEvolution')}</strong>
              <span className="text-muted-foreground ms-2" style={{ fontSize: '0.85rem' }}>
                {t('simulation.pollEvolutionDesc')}
              </span>
            </CardHeader>
            <CardBody>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart
                  data={pollChartData}
                  margin={{ top: 5, right: 20, bottom: 10, left: 10 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} />
                  <XAxis dataKey="round" tick={{ fontSize: 11, fill: ct.tickFill }} />
                  <YAxis
                    tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
                    domain={[0, 1]}
                    tick={{ fontSize: 11 }}
                  />
                  <Tooltip
                    formatter={numericTooltipFormatter((v: number) => `${(v * 100).toFixed(1)}%`)}
                    contentStyle={ct.tooltipStyle}
                  />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <ReferenceLine y={0.5} stroke={ct.refStroke} strokeDasharray="4 2" />
                  {/* Breakpoint annotations — rounds where poll leader changes */}
                  {pollBreakpoints.map((bp) => (
                    <ReferenceLine
                      key={bp.round}
                      x={bp.round}
                      stroke="#f28e2b"
                      strokeDasharray="3 2"
                      label={{
                        value: `↝ ${bp.to}`,
                        fontSize: 8,
                        fill: '#f28e2b',
                        position: 'insideTopRight',
                      }}
                    />
                  ))}
                  {candidateNames.map((name, i) => (
                    <Line
                      key={name}
                      type="monotone"
                      dataKey={name}
                      stroke={CANDIDATE_COLORS[i % CANDIDATE_COLORS.length]}
                      strokeWidth={2}
                      dot={{ r: 4 }}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </CardBody>
          </Card>

          {/* Chart 2: Bayesian regret per method */}
          <Card className="mb-4">
            <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
              <strong>{t('simulation.bayesianRegretPerRound')}</strong>
              <span className="text-muted-foreground ms-2" style={{ fontSize: '0.85rem' }}>
                {t('simulation.bayesianRegretPerRoundDesc')}
              </span>
            </CardHeader>
            <CardBody>
              <ResponsiveContainer width="100%" height={320}>
                <LineChart
                  data={regretChartData}
                  margin={{ top: 5, right: 20, bottom: 20, left: 10 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} />
                  <XAxis dataKey="round" tick={{ fontSize: 11, fill: ct.tickFill }} />
                  <YAxis tick={{ fontSize: 11, fill: ct.tickFill }} />
                  <Tooltip
                    formatter={numericTooltipFormatter((v: number) =>
                      v != null ? v.toFixed(4) : '—'
                    )}
                    contentStyle={ct.tooltipStyle}
                  />
                  <Legend verticalAlign="bottom" wrapperStyle={{ paddingTop: 10, fontSize: 10 }} />
                  {methodNames.map((method, i) => {
                    const isPlurality = method === 'plurality';
                    return (
                      <Line
                        key={method}
                        type="monotone"
                        dataKey={METHOD_LABELS[method] ?? method}
                        stroke={isPlurality ? '#dc3545' : METHOD_COLORS[i % METHOD_COLORS.length]}
                        strokeWidth={isPlurality ? 3 : 1.5}
                        dot={false}
                        activeDot={{ r: isPlurality ? 5 : 3 }}
                        connectNulls
                        zIndex={isPlurality ? 10 : 1}
                      />
                    );
                  })}
                </LineChart>
              </ResponsiveContainer>
            </CardBody>
          </Card>

          {/* Table: amplification summary */}
          <Card>
            <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
              <strong>{t('simulation.amplificationSummary')}</strong>
              <span className="text-muted-foreground ms-2" style={{ fontSize: '0.85rem' }}>
                {t('simulation.amplificationSummaryDesc')}
              </span>
            </CardHeader>
            <CardBody className="p-0">
              <Table className="[&_th]:p-1 [&_td]:p-1 [&_th]:text-left [&_td]:border-t [&_th]:border-b [&_td]:border-border [&_th]:border-border [&_*]:align-middle [&_th]:border [&_td]:border mb-0">
                <thead className="table-light">
                  <tr>
                    <th style={{ minWidth: 150 }}>{t('common.method')}</th>
                    <th className="text-center" style={{ minWidth: 120 }}>
                      {t('simulation.amplification')}
                    </th>
                    <th className="text-center">{t('simulation.verdict')}</th>
                    <th className="text-center" style={{ minWidth: 100 }}>
                      {t('simulation.winnerR0')}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(result.amplification_by_method)
                    .sort((a, b) => a[1] - b[1])
                    .map(([method, rate]) => {
                      const { label, variant } = amplificationLabel(rate);
                      const r0winner = result.rounds[0]?.methods[method]?.winner;
                      return (
                        <tr key={method}>
                          <td className="font-semibold ps-2">{METHOD_LABELS[method] ?? method}</td>
                          <td className="text-center">
                            <div
                              style={{
                                height: 6,
                                backgroundColor: '#e9ecef',
                                borderRadius: 3,
                                overflow: 'hidden',
                              }}
                            >
                              <div
                                style={{
                                  height: '100%',
                                  width: `${rate * 100}%`,
                                  backgroundColor:
                                    variant === 'success'
                                      ? '#198754'
                                      : variant === 'warning'
                                        ? '#ffc107'
                                        : '#dc3545',
                                  borderRadius: 3,
                                }}
                              />
                            </div>
                            <small className="text-muted-foreground">
                              {(rate * 100).toFixed(0)}%
                            </small>
                          </td>
                          <td className="text-center">
                            <Badge variant={variant} style={{ fontSize: '0.75rem' }}>
                              {label}
                            </Badge>
                          </td>
                          <td className="text-center text-muted-foreground text-sm">
                            {r0winner ?? '—'}
                          </td>
                        </tr>
                      );
                    })}
                </tbody>
              </Table>
            </CardBody>
          </Card>
        </>
      )}
    </div>
  );
};

export default BandwagonAnalysis;
