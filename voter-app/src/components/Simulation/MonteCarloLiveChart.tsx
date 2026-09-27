import React, { useMemo } from 'react';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
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
import { useChartTheme } from '../../hooks/useChartTheme';
import { MethodStreamStats } from '../../hooks/useMonteCarloStream';

import { numericTooltipFormatter } from '@/lib/rechartsFormatters';

const CANDIDATE_PALETTE = ['#4e79a7', '#f28e2b', '#e15759', '#76b7b2', '#59a14f', '#edc948'];

interface Props {
  isRunning: boolean;
  progress: number;
  iteration: number;
  total: number;
  condorcetRate: number;
  partialResults: Record<string, MethodStreamStats>;
  error: string | null;
  onStop: () => void;
}

const MonteCarloLiveChart: React.FC<Props> = ({
  isRunning,
  progress,
  iteration,
  total,
  condorcetRate,
  partialResults,
  error,
  onStop,
}) => {
  const { t } = useTranslation();
  const ct = useChartTheme();

  const candidates = useMemo(() => {
    const names = new Set<string>();
    Object.values(partialResults).forEach((s) =>
      Object.keys(s.winner_distribution).forEach((c) => names.add(c))
    );
    return [...names];
  }, [partialResults]);

  const colorMap = useMemo(
    () =>
      Object.fromEntries(
        candidates.map((c, i) => [c, CANDIDATE_PALETTE[i % CANDIDATE_PALETTE.length]])
      ),
    [candidates]
  );

  const chartData = useMemo(
    () =>
      Object.entries(partialResults).map(([method, stats]) => {
        const entry: Record<string, string | number> = { method };
        candidates.forEach((c) => {
          entry[c] = Math.round((stats.winner_distribution[c] ?? 0) * 100);
        });
        return entry;
      }),
    [partialResults, candidates]
  );

  if (error) return <Alert variant="danger">{error}</Alert>;

  if (!isRunning && iteration === 0) return null;

  return (
    <Card className="mb-4 border-primary">
      <CardHeader className="block space-y-0 border-b border-border px-4 py-2 flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2">
          {isRunning && <Spinner size="sm" />}
          <strong>
            {isRunning
              ? t('simulation.streamingProgress', { iteration, total })
              : t('simulation.streamingDone', { total })}
          </strong>
          {!isRunning && iteration > 0 && (
            <Badge variant="success">{t('simulation.complete')}</Badge>
          )}
        </div>
        {isRunning && (
          <Button variant="outline-danger" size="sm" onClick={onStop}>
            {t('simulation.stop')}
          </Button>
        )}
      </CardHeader>
      <CardBody>
        <Progress
          now={progress}
          label={`${progress}%`}
          variant="primary"
          className="mb-3"
          style={{ height: 18 }}
        />
        {condorcetRate > 0 && (
          <p className="text-muted-foreground text-sm mb-3">
            {t('simulation.condorcetExistsRate', { pct: (condorcetRate * 100).toFixed(1) })}
          </p>
        )}
        {chartData.length > 0 && candidates.length > 0 && (
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={chartData} margin={{ top: 4, bottom: 60, left: 0, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} />
              <XAxis
                dataKey="method"
                tick={{ fontSize: 10, fill: ct.tickFill }}
                angle={-40}
                textAnchor="end"
                interval={0}
              />
              <YAxis unit="%" tick={{ fontSize: 10, fill: ct.tickFill }} domain={[0, 100]} />
              <Tooltip
                formatter={numericTooltipFormatter((v: number) => `${v}%`)}
                contentStyle={ct.tooltipStyle}
              />
              {candidates.map((c) => (
                <Bar key={c} dataKey={c} stackId="a" name={c}>
                  {chartData.map((_, idx) => (
                    <Cell key={idx} fill={colorMap[c]} />
                  ))}
                </Bar>
              ))}
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardBody>
    </Card>
  );
};

export default MonteCarloLiveChart;
