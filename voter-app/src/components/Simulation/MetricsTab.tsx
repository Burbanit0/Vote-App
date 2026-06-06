import React, { useMemo, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { Modal } from '@/components/ui/modal';
import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { SimulationCompareResult } from '../../types';
import { METHOD_LABELS } from './simulationConstants';
import { useChartTheme } from '../../hooks/useChartTheme';
import EmptyChart from '../shared/EmptyChart';
import MetricTooltip from '../shared/MetricTooltip';
import MethodSimilarityGraph from './MethodSimilarityGraph';
import MajorityJudgmentChart from './MajorityJudgmentChart';
import type { MJResult } from './MajorityJudgmentChart';
import EvaluativeChart from './EvaluativeChart';
import type { EvaluativeResult } from './EvaluativeChart';
import { useTranslation } from 'react-i18next';

function avg(values: number[]): number {
  return values.length === 0 ? 0 : values.reduce((a, b) => a + b, 0) / values.length;
}

function round(value: number, decimals = 3): number {
  return Math.round(value * 10 ** decimals) / 10 ** decimals;
}

interface Props {
  comparisonResults: SimulationCompareResult[];
  allMethodNames: string[];
  numSimulations: number;
}

const MetricsTab: React.FC<Props> = ({ comparisonResults, allMethodNames, numSimulations }) => {
  const { t } = useTranslation();
  const ct = useChartTheme();
  const [showGraph, setShowGraph] = useState(false);

  const bayesianKey = t('simulation.bayesianRegret');
  const satisfactionKey = t('simulation.majoritySatisfaction');
  const vulnerabilityKey = t('simulation.strategicVulnerability');
  const lowerBetter = t('simulation.lowerBetter');
  const higherBetter = t('simulation.higherBetter');

  const metricsData = useMemo(() => {
    if (!comparisonResults.length) return [];
    return allMethodNames.map((method) => {
      const values = comparisonResults.map((r) => r.methods[method]);
      return {
        method: METHOD_LABELS[method] || method,
        [bayesianKey]: round(avg(values.map((v) => v.bayesian_regret ?? 0))),
        [satisfactionKey]: round(avg(values.map((v) => v.majority_satisfaction ?? 0))),
        [vulnerabilityKey]: round(avg(values.map((v) => v.strategic_vulnerability ?? 0))),
      };
    });
  }, [comparisonResults, allMethodNames]);

  // Pairwise agreement matrix derived from simulation results
  const agreementMatrix = useMemo(() => {
    if (!comparisonResults.length) return {} as Record<string, Record<string, number>>;
    const matrix: Record<string, Record<string, number>> = {};
    const n = comparisonResults.length;
    for (const a of allMethodNames) {
      matrix[a] = {};
      for (const b of allMethodNames) {
        if (a === b) {
          matrix[a][b] = 1;
          continue;
        }
        const agree = comparisonResults.filter(
          (r) => r.methods[a]?.winner != null && r.methods[a]?.winner === r.methods[b]?.winner
        ).length;
        matrix[a][b] = Math.round((agree / n) * 100) / 100;
      }
    }
    return matrix;
  }, [comparisonResults, allMethodNames]);

  // Median of Bayesian Regret — used as a reference line
  const medianRegret = useMemo(() => {
    if (!metricsData.length) return null;
    const sorted = [...metricsData].map((d) => d[bayesianKey] as number).sort((a, b) => a - b);
    return sorted[Math.floor(sorted.length / 2)];
  }, [metricsData]);

  const METRICS = [
    { key: bayesianKey, metricId: 'bayesian_regret' as const, color: '#e15759', note: lowerBetter },
    {
      key: satisfactionKey,
      metricId: 'majority_satisfaction' as const,
      color: '#59a14f',
      note: higherBetter,
    },
    {
      key: vulnerabilityKey,
      metricId: 'manipulability' as const,
      color: '#f28e2b',
      note: lowerBetter,
    },
  ];

  return (
    <>
      <Card className="mb-4">
        <CardHeader className="block space-y-0 border-b border-border px-4 py-2 flex items-center justify-between flex-wrap gap-2">
          <div>
            <strong>{t('simulation.comparativeMetrics')}</strong>
            <span className="text-muted-foreground ms-2" style={{ fontSize: '0.85rem' }}>
              {t('simulation.metricsSubtitle', { n: numSimulations })}
            </span>
          </div>
          {comparisonResults.length > 0 && (
            <Button
              size="sm"
              variant="outline-secondary"
              onClick={() => setShowGraph(true)}
              data-testid="open-graph-btn"
              style={{ fontSize: '0.78rem' }}
            >
              🕸 {t('graph.openButton')}
            </Button>
          )}
        </CardHeader>
        <CardBody>
          <div className="flex gap-4 mb-3 flex-wrap">
            {METRICS.map(({ key, metricId, color, note }) => (
              <span key={key} className="flex items-center gap-1">
                <span
                  style={{
                    display: 'inline-block',
                    width: 14,
                    height: 14,
                    borderRadius: 2,
                    backgroundColor: color,
                  }}
                />
                <small>
                  {key} <span className="text-muted-foreground">({note})</span>
                </small>
                <MetricTooltip metric={metricId} placement="bottom" />
              </span>
            ))}
          </div>

          {metricsData.length === 0 ? (
            <EmptyChart height={380} />
          ) : (
            <ResponsiveContainer width="100%" height={400}>
              <BarChart data={metricsData} margin={{ top: 20, bottom: 90, left: 10, right: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} />
                <XAxis
                  dataKey="method"
                  tick={{ fontSize: 11, fill: ct.tickFill }}
                  angle={-45}
                  textAnchor="end"
                  interval={0}
                />
                <YAxis domain={[0, 1]} tick={{ fontSize: 11, fill: ct.tickFill }} />
                <Tooltip formatter={(v: number) => v.toFixed(3)} contentStyle={ct.tooltipStyle} />

                {/* Median reference line for Bayesian Regret */}
                {medianRegret !== null && (
                  <ReferenceLine
                    y={medianRegret}
                    stroke="#6c757d"
                    strokeDasharray="5 3"
                    label={{
                      value: `${t('simulation.median')}: ${medianRegret.toFixed(3)}`,
                      fontSize: 9,
                      fill: '#6c757d',
                      position: 'insideTopRight',
                    }}
                  />
                )}

                {METRICS.map(({ key, color }) => (
                  <Bar key={key} dataKey={key} fill={color} maxBarSize={28}>
                    <LabelList
                      dataKey={key}
                      position="top"
                      style={{ fontSize: 8, fill: ct.tickFill }}
                      formatter={(v: unknown) => (typeof v === 'number' ? v.toFixed(2) : '')}
                    />
                  </Bar>
                ))}
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardBody>
      </Card>

      {/* Majority Judgment visualization — shown when MJ is in the results */}
      {(() => {
        const mjResult = comparisonResults[0]?.methods?.['majority_judgment'] as unknown as
          | (Record<string, unknown> & {
              mj_grade_distributions?: Record<string, number[]>;
              mj_grades?: Record<string, Record<string, number>>;
              mj_medians?: Record<string, string>;
              mj_scores?: Record<string, number>;
              winner?: string | null;
            })
          | undefined;
        if (!mjResult?.mj_grade_distributions) return null;
        const allCandidates = Object.keys(mjResult.mj_grade_distributions);
        const mjData: MJResult = {
          winner: mjResult.winner ?? null,
          grades: mjResult.mj_grades ?? {},
          medians: mjResult.mj_medians ?? {},
          scores: mjResult.mj_scores ?? {},
          grade_distributions: mjResult.mj_grade_distributions,
        };
        return (
          <Card className="mb-4" data-testid="mj-card">
            <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
              <strong>{t('mj.chartTitle')}</strong>
              <span className="text-muted-foreground ms-2" style={{ fontSize: '0.85rem' }}>
                {t('mj.chartSubtitle')}
              </span>
            </CardHeader>
            <CardBody>
              <MajorityJudgmentChart mjResult={mjData} candidates={allCandidates} />
            </CardBody>
          </Card>
        );
      })()}

      {/* Evaluative voting chart */}
      {(() => {
        const evRaw = comparisonResults[0]?.methods?.['evaluative'] as unknown as
          | (Record<string, unknown> & {
              ev_scores?: Record<string, number>;
              ev_distribution?: Record<string, Record<string, number>>;
              winner?: string | null;
            })
          | undefined;
        if (!evRaw?.ev_distribution) return null;
        const allCandidates = Object.keys(evRaw.ev_distribution);
        const evData: EvaluativeResult = {
          winner: evRaw.winner ?? null,
          scores: evRaw.ev_scores ?? {},
          ev_distribution: evRaw.ev_distribution as Record<
            string,
            { '+1': number; '0': number; '-1': number }
          >,
        };
        return (
          <Card className="mb-4" data-testid="ev-card">
            <CardHeader className="block space-y-0 border-b border-border px-4 py-2">
              <strong>{t('ev.chartTitle')}</strong>
              <span className="text-muted-foreground ms-2" style={{ fontSize: '0.85rem' }}>
                {t('ev.chartSubtitle')}
              </span>
            </CardHeader>
            <CardBody>
              <EvaluativeChart evResult={evData} candidates={allCandidates} />
            </CardBody>
          </Card>
        );
      })()}

      {/* Similarity graph modal */}
      <Modal show={showGraph} onHide={() => setShowGraph(false)} size="xl" centered>
        <Modal.Header closeButton>
          <Modal.Title style={{ fontSize: '1rem' }}>{t('graph.title')}</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <MethodSimilarityGraph agreementMatrix={agreementMatrix} height={440} />
        </Modal.Body>
      </Modal>
    </>
  );
};

export default MetricsTab;
