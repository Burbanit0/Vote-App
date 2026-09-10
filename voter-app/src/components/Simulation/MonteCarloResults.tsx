import React, { useMemo, useState } from 'react';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { Check, Control, Range, Select } from '@/components/ui/form-controls';
import { Col, Row } from '@/components/ui/grid';
import { Progress } from '@/components/ui/progress';
import { Spinner } from '@/components/ui/spinner';
import { Table } from '@/components/ui/table';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ErrorBar,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Trans, useTranslation } from 'react-i18next';
import { MonteCarloResult } from '../../types';
import { getMonteCarlo, MonteCarloParams } from '../../services/simulationCompareApi';
import ResponsiveTable from '../shared/ResponsiveTable';
import SkeletonCard from '../shared/SkeletonCard';
import { useChartTheme } from '../../hooks/useChartTheme';
import { useMonteCarloStream } from '../../hooks/useMonteCarloStream';
import MonteCarloLiveChart from './MonteCarloLiveChart';
import MonteCarloRaceChart from './MonteCarloRaceChart';
import MonteCarloConvergencePanel from './MonteCarloConvergencePanel';
import MethodSimilarityGraph, {
  flatToMatrix,
  partialResultsToMatrix,
} from './MethodSimilarityGraph';
import { useSimulationWorker } from '../../hooks/useSimulationWorker';
import MetricTooltip from '../shared/MetricTooltip';

import { numericTooltipFormatter } from '@/lib/rechartsFormatters';

const CANDIDATE_PALETTE = ['#4e79a7', '#f28e2b', '#e15759', '#76b7b2', '#59a14f', '#edc948'];

// ── Helpers ────────────────────────────────────────────────────────────────

function cellStyle(rate: number, isDark: boolean): React.CSSProperties {
  if (isDark) {
    if (rate >= 0.8) return { backgroundColor: '#1a3a2a', color: '#75b798' };
    if (rate >= 0.5) return { backgroundColor: '#332b00', color: '#c0964e' };
    return { backgroundColor: '#3a1a1e', color: '#ea868f' };
  }
  if (rate >= 0.8) return { backgroundColor: '#d4edda', color: '#155724' };
  if (rate >= 0.5) return { backgroundColor: '#fff3cd', color: '#856404' };
  return { backgroundColor: '#f8d7da', color: '#721c24' };
}

function parseAgreementKey(key: string): [string, string] {
  const idx = key.indexOf('|');
  return [key.slice(0, idx), key.slice(idx + 1)];
}

// ── Component ──────────────────────────────────────────────────────────────

interface Props {
  baseParams: { num_voters?: number; candidates?: string[]; ideology_distribution?: string };
}

const MonteCarloResults: React.FC<Props> = ({ baseParams }) => {
  const { t } = useTranslation();
  const ct = useChartTheme();
  const { dispatch: workerDispatch } = useSimulationWorker();
  const [sortByRegret, setSortByRegret] = useState(false);
  const [numRuns, setNumRuns] = useState(100);
  const [numVoters, setNumVoters] = useState(baseParams.num_voters ?? 150);
  const [ideologyDist, setIdeologyDist] = useState(baseParams.ideology_distribution ?? 'random');
  const [result, setResult] = useState<MonteCarloResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [streamMatrix, setStreamMatrix] = useState<Record<string, Record<string, number>>>({});
  const [error, setError] = useState<string | null>(null);
  const [useStreaming, setUseStreaming] = useState(true);

  const stream = useMonteCarloStream();

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
      simple_score: t('methods.simple_score.label'),
      star_voting: t('methods.star_voting.label'),
      median_voting: t('methods.median_voting.label'),
      mean_median_hybrid: t('methods.mean_median_hybrid.label'),
      variance_based: t('methods.variance_based.label'),
    }),
    [t]
  );

  const ideologyOptions = [
    { value: 'random', label: t('ideology.random') },
    { value: 'centrist', label: t('ideology.centrist') },
    { value: 'polarized', label: t('ideology.polarized') },
    { value: 'left_skewed', label: t('ideology.left_skewed') },
    { value: 'right_skewed', label: t('ideology.right_skewed') },
  ];

  const runMC = async () => {
    setResult(null);
    setError(null);

    if (useStreaming) {
      stream.reset();
      stream.start({
        num_iterations: numRuns,
        num_voters: numVoters,
        candidates: baseParams.candidates,
        ideology: ideologyDist,
      });
      return;
    }

    setLoading(true);
    try {
      const params: MonteCarloParams = {
        num_runs: numRuns,
        num_voters: numVoters,
        candidates: baseParams.candidates,
        ideology_distribution: ideologyDist,
      };
      setResult(await getMonteCarlo(params));
    } catch {
      setError(t('simulation.errMonteCarlo'));
    } finally {
      setLoading(false);
    }
  };

  // ── Offload matrix computation to worker on each streaming tick ───────
  React.useEffect(() => {
    const keys = Object.keys(stream.partialResults);
    if (keys.length < 2) return;
    workerDispatch('COMPUTE_MATRIX', { partialResults: stream.partialResults })
      .then(({ matrix }) => setStreamMatrix(matrix))
      .catch(() => setStreamMatrix(partialResultsToMatrix(stream.partialResults)));
  }, [stream.partialResults, workerDispatch]);

  // ── Derived ────────────────────────────────────────────────────────────

  const methodNames = useMemo(() => (result ? Object.keys(result.methods) : []), [result]);

  // All unique candidate names seen across winner distributions
  const candidateNames = useMemo(() => {
    if (!result) return [] as string[];
    const names = new Set<string>();
    Object.values(result.methods).forEach((m) =>
      Object.keys(m.winner_distribution).forEach((c) => names.add(c))
    );
    return [...names];
  }, [result]);

  const colorMap = useMemo(
    () =>
      Object.fromEntries(
        candidateNames.map((c, i) => [c, CANDIDATE_PALETTE[i % CANDIDATE_PALETTE.length]])
      ),
    [candidateNames]
  );

  // Bar chart data: regret mean + error value, optionally sorted
  const regretBarData = useMemo(() => {
    const data = methodNames.map((m) => {
      const s = result!.methods[m];
      const ci = s.bayesian_regret_ci_95;
      const mean = s.bayesian_regret_mean ?? 0;
      const errorVal = ci[1] != null ? ci[1] - mean : 0;
      return { method: METHOD_LABELS[m] ?? m, regret: mean, errorVal };
    });
    return sortByRegret ? [...data].sort((a, b) => a.regret - b.regret) : data;
  }, [result, methodNames, sortByRegret]);

  // Stability table sorted ascending (most stable first)
  const stabilityRows = useMemo(
    () =>
      methodNames
        .map((m) => {
          const s = result!.methods[m];
          const pct = s.most_common_winner ? (s.winner_distribution[s.most_common_winner] ?? 0) : 0;
          return {
            method: m,
            winner: s.most_common_winner,
            pct,
            stability: s.winner_stability,
            compliance: s.condorcet_compliance_rate,
          };
        })
        .sort((a, b) => a.stability - b.stability),
    [result, methodNames]
  );

  // Agreement matrix row/col order
  const agreementMethodNames = useMemo(() => {
    if (!result) return [] as string[];
    const seen = new Set<string>();
    Object.keys(result.inter_method_agreement).forEach((key) => {
      const [a, b] = parseAgreementKey(key);
      seen.add(a);
      seen.add(b);
    });
    return [...seen];
  }, [result]);

  const getAgreement = (a: string, b: string): number | null => {
    if (!result) return null;
    if (a === b) return 1;
    return (
      result.inter_method_agreement[`${a}|${b}`] ??
      result.inter_method_agreement[`${b}|${a}`] ??
      null
    );
  };

  // ── Render ─────────────────────────────────────────────────────────────

  return (
    <div>
      {/* Config */}
      <Card className="mb-4">
        <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
          <strong>{t('simulation.monteCarloConfig')}</strong>
        </CardHeader>
        <CardBody>
          <Row className="g-3 items-end">
            <Col md={3}>
              <label className="mb-1 inline-block text-sm mb-1">
                {t('simulation.monteCarloSims')} : <strong>{numRuns}</strong>
              </label>
              <Range
                min={20}
                max={500}
                step={10}
                value={numRuns}
                onChange={(e) => setNumRuns(Number(e.target.value))}
              />
            </Col>
            <Col md={2}>
              <label className="mb-1 inline-block text-sm mb-1">
                {t('simulation.votersPerSim')}
              </label>
              <Control
                size="sm"
                type="number"
                min={50}
                max={500}
                value={numVoters}
                onChange={(e) => setNumVoters(Number(e.target.value))}
              />
            </Col>
            <Col md={3}>
              <label className="mb-1 inline-block text-sm mb-1">
                {t('simulation.distribution')}
              </label>
              <Select
                size="sm"
                value={ideologyDist}
                onChange={(e) => setIdeologyDist(e.target.value)}
              >
                {ideologyOptions.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </Select>
            </Col>
            <Col md={2}>
              <Button
                data-testid="mc-run"
                variant="primary"
                size="sm"
                className="w-full"
                onClick={runMC}
                disabled={loading || stream.isRunning}
              >
                {loading ? (
                  <>
                    <Spinner size="sm" className="me-2" />
                    {t('simulation.runningEllipsis')}
                  </>
                ) : (
                  t('simulation.runMonteCarlo')
                )}
              </Button>
            </Col>
            <Col md={2} className="flex items-end">
              <Check
                type="switch"
                id="streaming-toggle"
                label={<span className="text-sm">{t('simulation.useStreaming')}</span>}
                checked={useStreaming}
                onChange={(e) => setUseStreaming(e.target.checked)}
                disabled={loading || stream.isRunning}
              />
            </Col>
          </Row>
          <p className="text-muted-foreground text-sm mt-2 mb-0">
            {t('simulation.monteCarloInfo')}
          </p>
        </CardBody>
      </Card>

      {(error || stream.error) && <Alert variant="danger">{error ?? stream.error}</Alert>}

      {loading && (
        <Row className="g-3 mb-2">
          {[220, 300, 200].map((h, i) => (
            <Col key={i} md={4}>
              <SkeletonCard height={h} />
            </Col>
          ))}
        </Row>
      )}

      {/* Live streaming chart */}
      <MonteCarloLiveChart
        isRunning={stream.isRunning}
        progress={stream.progress}
        iteration={stream.iteration}
        total={stream.total}
        condorcetRate={stream.condorcetRate}
        partialResults={stream.partialResults}
        error={null}
        onStop={() => stream.stop()}
      />

      {/* Race chart — visible once checkpoints exist */}
      <MonteCarloRaceChart
        regretHistory={stream.regretHistory}
        iterationCheckpoints={stream.iterationCheckpoints}
        partialResults={stream.partialResults}
        isRunning={stream.isRunning}
      />

      {/* Convergence panels — visible from first progress event */}
      <MonteCarloConvergencePanel
        regretHistory={stream.regretHistory}
        agreementHistory={stream.agreementHistory}
        ciHalfLatest={stream.ciHalfLatest}
        iterationCheckpoints={stream.iterationCheckpoints}
        iteration={stream.iteration}
        isRunning={stream.isRunning}
      />

      {/* Similarity graph — shown once streaming has partial results */}
      {Object.keys(stream.partialResults).length > 1 && (
        <Card className="mb-4" data-testid="mc-stream-graph">
          <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
            <strong>{t('graph.title')}</strong>
            <span className="text-muted-foreground ms-2" style={{ fontSize: '0.85rem' }}>
              {t('graph.subtitle')}
            </span>
          </CardHeader>
          <CardBody>
            <MethodSimilarityGraph agreementMatrix={streamMatrix} />
          </CardBody>
        </Card>
      )}

      {!result && !loading && !stream.isRunning && stream.iteration === 0 && (
        <Alert variant="info">
          <Trans
            i18nKey="simulation.monteCarloPrompt"
            values={{ sec: Math.round(((numRuns * numVoters) / 1000) * 2) }}
          />
        </Alert>
      )}

      {result && (
        <div data-testid="mc-results">
          <Alert variant="secondary" className="py-2 mb-4">
            <Trans
              i18nKey="simulation.monteCarloSummary"
              values={{
                numRuns: result.num_runs,
                numVoters: result.num_voters_per_run,
                pct: (result.condorcet_winner_exists_rate * 100).toFixed(0),
              }}
            />
          </Alert>

          {/* 1. Regret bar chart with CI error bars */}
          <Card className="mb-4">
            <CardHeader className="block space-y-0 border-b border-border px-4 py-2 flex items-center justify-between flex-wrap gap-2">
              <div>
                <strong>{t('simulation.bayesianRegretCI')}</strong>
                <MetricTooltip metric="bayesian_regret" placement="bottom" />
                <span className="text-muted-foreground ms-2" style={{ fontSize: '0.85rem' }}>
                  {t('simulation.bayesianRegretCIDesc')}
                </span>
              </div>
              <Button
                size="sm"
                variant={sortByRegret ? 'secondary' : 'outline-secondary'}
                onClick={() => setSortByRegret(!sortByRegret)}
                style={{ fontSize: '0.78rem' }}
              >
                {sortByRegret ? t('simulation.originalOrder') : t('simulation.sortByRegret')}
              </Button>
            </CardHeader>
            <CardBody>
              <ResponsiveContainer width="100%" height={380}>
                <BarChart
                  data={regretBarData}
                  margin={{ top: 10, bottom: 80, left: 10, right: 10 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} />
                  <XAxis
                    dataKey="method"
                    tick={{ fontSize: 10, fill: ct.tickFill }}
                    angle={-45}
                    textAnchor="end"
                    interval={0}
                  />
                  <YAxis tick={{ fontSize: 10, fill: ct.tickFill }} />
                  <Tooltip
                    formatter={numericTooltipFormatter((v: number) => v.toFixed(4))}
                    contentStyle={ct.tooltipStyle}
                  />
                  <Bar dataKey="regret" name={t('simulation.bayesianRegret')} fill="#4e79a7">
                    {regretBarData.map((_, i) => (
                      <Cell key={i} fill="#4e79a7" />
                    ))}
                    <ErrorBar
                      dataKey="errorVal"
                      width={6}
                      strokeWidth={3}
                      stroke="#e15759"
                      direction="y"
                    />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </CardBody>
          </Card>

          {/* 2. Inter-method agreement heatmap */}
          <Card className="mb-4">
            <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
              <strong>{t('simulation.interMethodAgreement')}</strong>
              <span className="text-muted-foreground ms-2" style={{ fontSize: '0.85rem' }}>
                {t('simulation.interMethodAgreementDesc')}
              </span>
            </CardHeader>
            <CardBody>
              <div className="flex gap-3 mb-3">
                {[
                  { bg: '#d4edda', color: '#155724', label: t('simulation.agreement80') },
                  { bg: '#fff3cd', color: '#856404', label: t('simulation.agreement50_80') },
                  { bg: '#f8d7da', color: '#721c24', label: t('simulation.agreementLess50') },
                ].map(({ bg, color, label }) => (
                  <span key={label} className="flex items-center gap-1">
                    <span
                      style={{
                        display: 'inline-block',
                        width: 14,
                        height: 14,
                        backgroundColor: bg,
                        border: `1px solid ${color}`,
                        borderRadius: 2,
                      }}
                    />
                    <small style={{ color }}>{label}</small>
                  </span>
                ))}
              </div>
              <ResponsiveTable>
                <Table
                  className="[&_th]:p-1 [&_td]:p-1 [&_th]:text-left [&_td]:border-t [&_th]:border-b [&_td]:border-border [&_th]:border-border [&_*]:align-middle [&_th]:border [&_td]:border text-center"
                  style={{ minWidth: 400 }}
                >
                  <thead className="table-light">
                    <tr>
                      <th style={{ minWidth: 120, textAlign: 'left' }}>{t('common.method')}</th>
                      {agreementMethodNames.map((m) => (
                        <th key={m} style={{ minWidth: 80, fontSize: '0.75rem' }}>
                          {METHOD_LABELS[m] ?? m}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {agreementMethodNames.map((rowMethod) => (
                      <tr key={rowMethod}>
                        <td className="text-left ps-1 font-semibold" style={{ fontSize: '0.8rem' }}>
                          {METHOD_LABELS[rowMethod] ?? rowMethod}
                        </td>
                        {agreementMethodNames.map((colMethod) => {
                          const rate = getAgreement(rowMethod, colMethod);
                          if (rowMethod === colMethod) {
                            return (
                              <td
                                key={colMethod}
                                style={{ backgroundColor: '#e9ecef', color: '#6c757d' }}
                              >
                                —
                              </td>
                            );
                          }
                          return (
                            <td
                              key={colMethod}
                              style={rate != null ? cellStyle(rate, ct.isDark) : undefined}
                            >
                              {rate != null ? `${(rate * 100).toFixed(0)}%` : '?'}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </Table>
              </ResponsiveTable>
            </CardBody>
          </Card>

          {/* 3. Similarity graph */}
          <Card className="mb-4">
            <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
              <strong>{t('graph.title')}</strong>
              <span className="text-muted-foreground ms-2" style={{ fontSize: '0.85rem' }}>
                {t('graph.subtitle')}
              </span>
            </CardHeader>
            <CardBody>
              <MethodSimilarityGraph
                agreementMatrix={flatToMatrix(result.inter_method_agreement)}
              />
            </CardBody>
          </Card>

          {/* 4. Stability table */}
          <Card>
            <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
              <strong>{t('simulation.winnerStability')}</strong>
              <span className="text-muted-foreground ms-2" style={{ fontSize: '0.85rem' }}>
                {t('simulation.winnerStabilityDesc')}
              </span>
            </CardHeader>
            <CardBody className="p-0">
              <Table className="[&_th]:p-1 [&_td]:p-1 [&_th]:text-left [&_td]:border-t [&_th]:border-b [&_td]:border-border [&_th]:border-border [&_*]:align-middle [&_th]:border [&_td]:border mb-0">
                <thead className="table-light">
                  <tr>
                    <th style={{ minWidth: 150 }}>{t('common.method')}</th>
                    <th className="text-center">{t('simulation.mostFrequentWinnerLabel')}</th>
                    <th className="text-center" style={{ minWidth: 80 }}>
                      {t('simulation.pctSims')}
                    </th>
                    <th style={{ minWidth: 160 }}>{t('simulation.stability')}</th>
                    <th className="text-center" title={t('simulation.condorcetCompliance')}>
                      {t('simulation.condorcetCompliance')}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {stabilityRows.map(({ method, winner, pct, stability, compliance }) => (
                    <tr key={method}>
                      <td className="font-semibold ps-2">{METHOD_LABELS[method] ?? method}</td>
                      <td className="text-center">
                        {winner ? (
                          <Badge
                            style={{
                              backgroundColor: colorMap[winner] ?? '#999',
                              fontSize: '0.75rem',
                            }}
                          >
                            {winner}
                          </Badge>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </td>
                      <td className="text-center">
                        <strong>{(pct * 100).toFixed(0)}%</strong>
                      </td>
                      <td>
                        <div className="flex items-center gap-2">
                          <Progress
                            now={(1 - stability) * 100}
                            variant={
                              stability < 0.25 ? 'success' : stability < 0.6 ? 'warning' : 'danger'
                            }
                            style={{ flex: 1, height: 8 }}
                          />
                          <small className="text-muted-foreground" style={{ minWidth: 36 }}>
                            {(stability * 100).toFixed(0)}%
                          </small>
                        </div>
                      </td>
                      <td className="text-center">
                        {compliance != null ? (
                          `${(compliance * 100).toFixed(0)}%`
                        ) : (
                          <span className="text-muted-foreground text-sm">N/A</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </CardBody>
          </Card>
        </div>
      )}
    </div>
  );
};

export default MonteCarloResults;
