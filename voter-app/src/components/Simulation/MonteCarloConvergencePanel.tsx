import React, { useMemo } from 'react';
import { Badge, Card, Col, Row } from 'react-bootstrap';
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell,
  ComposedChart, Legend, Line, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { useTranslation } from 'react-i18next';
import { useChartTheme } from '../../hooks/useChartTheme';

// ── WCAG-AA accessible palette for method lines ───────────────────────────────
const METHOD_COLORS = [
  '#005CAB', // blue
  '#C8590A', // orange
  '#007A33', // green
  '#7B2D8B', // purple
  '#9C3A00', // brown-red
];

interface Props {
  regretHistory:        Record<string, number[]>;
  agreementHistory:     number[];
  ciHalfLatest:         Record<string, number | null>;
  iterationCheckpoints: number[];
  iteration:            number;
  isRunning:            boolean;
}

// ── Panel 1 helpers ───────────────────────────────────────────────────────────

function useTop5Methods(regretHistory: Record<string, number[]>): string[] {
  return useMemo(() => {
    const methods = Object.keys(regretHistory ?? {});
    if (methods.length === 0) return [];
    // Rank by last known mean regret (lower = better)
    return [...methods]
      .filter((m) => (regretHistory[m]?.length ?? 0) > 0)
      .sort((a, b) => {
        const aLast = regretHistory[a].at(-1) ?? Infinity;
        const bLast = regretHistory[b].at(-1) ?? Infinity;
        return aLast - bLast;
      })
      .slice(0, 5);
  }, [regretHistory]);
}

// ── Sub-components ────────────────────────────────────────────────────────────

const RegretConvergenceChart: React.FC<{
  regretHistory:        Record<string, number[]>;
  iterationCheckpoints: number[];
  top5:                 string[];
  ct:                   ReturnType<typeof useChartTheme>;
  t:                    (k: string) => string;
}> = ({ regretHistory, iterationCheckpoints, top5, ct, t }) => {
  const data = useMemo(
    () =>
      iterationCheckpoints.map((iter, idx) => {
        const point: Record<string, number | string> = { iter };
        top5.forEach((m) => {
          point[m] = regretHistory[m]?.[idx] ?? 0;
        });
        return point;
      }),
    [regretHistory, iterationCheckpoints, top5]
  );

  if (data.length === 0) return null;

  return (
    <ResponsiveContainer width="100%" height={220}>
      <ComposedChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} />
        <XAxis
          dataKey="iter"
          tick={{ fontSize: 10, fill: ct.tickFill }}
          label={{ value: t('simulation.convergenceIter'), position: 'insideBottomRight', offset: -4, fontSize: 10, fill: ct.tickFill }}
        />
        <YAxis tick={{ fontSize: 10, fill: ct.tickFill }} width={52} tickFormatter={(v) => v.toFixed(3)} />
        <Tooltip
          contentStyle={ct.tooltipStyle}
          formatter={(v: number, name: string) => [v.toFixed(5), name]}
          labelFormatter={(l) => `${t('simulation.convergenceIter')} ${l}`}
        />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        {top5.map((m, idx) => (
          <Line
            key={m}
            type="monotone"
            dataKey={m}
            stroke={METHOD_COLORS[idx % METHOD_COLORS.length]}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        ))}
      </ComposedChart>
    </ResponsiveContainer>
  );
};

const AgreementChart: React.FC<{
  agreementHistory:     number[];
  iterationCheckpoints: number[];
  ct:                   ReturnType<typeof useChartTheme>;
  t:                    (k: string) => string;
}> = ({ agreementHistory, iterationCheckpoints, ct, t }) => {
  const data = useMemo(
    () =>
      iterationCheckpoints.map((iter, idx) => ({
        iter,
        rate: Math.round((agreementHistory[idx] ?? 0) * 100),
      })),
    [agreementHistory, iterationCheckpoints]
  );

  if (data.length === 0) return null;

  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
        <defs>
          <linearGradient id="agreementGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor="#005CAB" stopOpacity={0.25} />
            <stop offset="95%" stopColor="#005CAB" stopOpacity={0.04} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} />
        <XAxis
          dataKey="iter"
          tick={{ fontSize: 10, fill: ct.tickFill }}
          label={{ value: t('simulation.convergenceIter'), position: 'insideBottomRight', offset: -4, fontSize: 10, fill: ct.tickFill }}
        />
        <YAxis tick={{ fontSize: 10, fill: ct.tickFill }} domain={[0, 100]} unit="%" width={40} />
        <Tooltip
          contentStyle={ct.tooltipStyle}
          formatter={(v: number) => [`${v}%`, t('simulation.methodAgreement')]}
          labelFormatter={(l) => `${t('simulation.convergenceIter')} ${l}`}
        />
        <ReferenceLine y={80} stroke="#007A33" strokeDasharray="4 3" label={{ value: '80%', fill: '#007A33', fontSize: 10 }} />
        <ReferenceLine y={50} stroke="#C8590A" strokeDasharray="4 3" label={{ value: '50%', fill: '#C8590A', fontSize: 10 }} />
        <Area
          type="monotone"
          dataKey="rate"
          stroke="#005CAB"
          strokeWidth={2}
          fill="url(#agreementGrad)"
          isAnimationActive={false}
          name={t('simulation.methodAgreement')}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
};

const CIStabilityChart: React.FC<{
  ciHalfLatest: Record<string, number | null>;
  ct:           ReturnType<typeof useChartTheme>;
  t:            (k: string) => string;
}> = ({ ciHalfLatest, ct, t }) => {
  const data = useMemo(
    () =>
      Object.entries(ciHalfLatest)
        .filter(([, v]) => v !== null && v !== undefined)
        .map(([m, v]) => ({ method: m, ci: v as number }))
        .sort((a, b) => a.ci - b.ci),
    [ciHalfLatest]
  );

  if (data.length === 0) return null;

  const ciColor = (ci: number) => {
    if (ci < 0.01) return '#007A33'; // green — stable
    if (ci < 0.05) return '#C8590A'; // orange — acceptable
    return '#B71C1C';                // red — unstable
  };

  return (
    <ResponsiveContainer width="100%" height={Math.max(160, data.length * 26)}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 4, right: 40, bottom: 4, left: 4 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} horizontal={false} />
        <XAxis
          type="number"
          tick={{ fontSize: 10, fill: ct.tickFill }}
          tickFormatter={(v) => v.toFixed(3)}
        />
        <YAxis
          type="category"
          dataKey="method"
          tick={{ fontSize: 10, fill: ct.tickFill }}
          width={110}
        />
        <Tooltip
          contentStyle={ct.tooltipStyle}
          formatter={(v: number) => [v.toFixed(5), t('simulation.ciHalfWidth')]}
        />
        <Bar dataKey="ci" name={t('simulation.ciHalfWidth')} radius={[0, 3, 3, 0]} isAnimationActive={false}>
          {data.map((entry) => (
            <Cell key={entry.method} fill={ciColor(entry.ci)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
};

// ── Main component ────────────────────────────────────────────────────────────

const MonteCarloConvergencePanel: React.FC<Props> = ({
  regretHistory,
  agreementHistory,
  ciHalfLatest,
  iterationCheckpoints,
  iteration,
  isRunning,
}) => {
  const { t } = useTranslation();
  const ct    = useChartTheme();
  const top5  = useTop5Methods(regretHistory);

  const hasData = iterationCheckpoints.length > 0;
  if (!hasData) return null;

  const showCI = iteration >= 50;

  return (
    <div className="mt-3">
      <Row className="g-3">
        {/* Panel 1 — Regret convergence */}
        <Col xs={12} lg={showCI ? 5 : 6}>
          <Card className="h-100">
            <Card.Header className="py-2">
              <strong style={{ fontSize: '0.88rem' }}>{t('simulation.regretConvergence')}</strong>
              {isRunning && (
                <Badge bg="primary" className="ms-2" style={{ fontSize: '0.65rem' }}>
                  {t('simulation.live')}
                </Badge>
              )}
              <div className="text-muted" style={{ fontSize: '0.75rem' }}>
                {t('simulation.regretConvergenceDesc')}
              </div>
            </Card.Header>
            <Card.Body className="p-2">
              <RegretConvergenceChart
                regretHistory={regretHistory}
                iterationCheckpoints={iterationCheckpoints}
                top5={top5}
                ct={ct}
                t={t}
              />
            </Card.Body>
          </Card>
        </Col>

        {/* Panel 2 — Agreement rate */}
        <Col xs={12} lg={showCI ? 4 : 6}>
          <Card className="h-100">
            <Card.Header className="py-2">
              <strong style={{ fontSize: '0.88rem' }}>{t('simulation.methodAgreementTitle')}</strong>
              {isRunning && (
                <Badge bg="primary" className="ms-2" style={{ fontSize: '0.65rem' }}>
                  {t('simulation.live')}
                </Badge>
              )}
              <div className="text-muted" style={{ fontSize: '0.75rem' }}>
                {t('simulation.methodAgreementDesc')}
              </div>
            </Card.Header>
            <Card.Body className="p-2">
              <AgreementChart
                agreementHistory={agreementHistory}
                iterationCheckpoints={iterationCheckpoints}
                ct={ct}
                t={t}
              />
            </Card.Body>
          </Card>
        </Col>

        {/* Panel 3 — CI stability (shown once enough data) */}
        {showCI && (
          <Col xs={12} lg={3}>
            <Card className="h-100">
              <Card.Header className="py-2">
                <strong style={{ fontSize: '0.88rem' }}>{t('simulation.ciStability')}</strong>
                <div className="text-muted" style={{ fontSize: '0.75rem' }}>
                  {t('simulation.ciStabilityDesc')}
                </div>
              </Card.Header>
              <Card.Body className="p-2">
                <div className="d-flex gap-2 mb-2 flex-wrap">
                  {[
                    { color: '#007A33', label: t('simulation.ciStable') },
                    { color: '#C8590A', label: t('simulation.ciModerate') },
                    { color: '#B71C1C', label: t('simulation.ciUnstable') },
                  ].map(({ color, label }) => (
                    <span key={label} className="d-flex align-items-center gap-1" style={{ fontSize: '0.7rem' }}>
                      <span style={{ width: 10, height: 10, borderRadius: 2, backgroundColor: color, display: 'inline-block' }} />
                      {label}
                    </span>
                  ))}
                </div>
                <CIStabilityChart ciHalfLatest={ciHalfLatest} ct={ct} t={t} />
              </Card.Body>
            </Card>
          </Col>
        )}
      </Row>
    </div>
  );
};

export default MonteCarloConvergencePanel;
