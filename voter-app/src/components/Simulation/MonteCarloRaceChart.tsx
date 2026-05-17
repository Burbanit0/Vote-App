import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Badge, Card, Form } from 'react-bootstrap';
import {
  Area, AreaChart, CartesianGrid, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { useTranslation } from 'react-i18next';
import { useChartTheme } from '../../hooks/useChartTheme';
import { MethodStreamStats } from '../../hooks/useMonteCarloStream';

// ── Palette ───────────────────────────────────────────────────────────────────

const RACE_COLORS = [
  '#1a56cc', '#b35c00', '#b71c1c', '#006957',
  '#1b5e20', '#544200', '#7B2D8B', '#005f73',
];

// ── Types ─────────────────────────────────────────────────────────────────────

interface HistoryPoint {
  iter:      number;
  allMethods: Record<string, number>;  // candidate → max pct across all methods
  byMethod:   Record<string, Record<string, number>>;  // method → {candidate: pct}
}

type ViewMode = 'all' | 'method';

interface Props {
  regretHistory:        Record<string, number[]>;
  iterationCheckpoints: number[];
  partialResults:       Record<string, MethodStreamStats>;
  isRunning:            boolean;
}

// ── Tooltip ───────────────────────────────────────────────────────────────────

const RaceTooltip = ({ active, payload, label, t }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded p-2" style={{
      background: 'var(--bs-body-bg)',
      border: '1px solid var(--bs-border-color)',
      fontSize: '0.75rem',
    }}>
      <strong>{t('simulation.convergenceIter')} {label}</strong>
      {payload.map((p: any) => (
        <div key={p.dataKey} style={{ color: p.color }}>
          {p.dataKey}: <strong>{Math.round(p.value * 100)}%</strong>
        </div>
      ))}
    </div>
  );
};

// ── Main component ────────────────────────────────────────────────────────────

const MonteCarloRaceChart: React.FC<Props> = ({
  regretHistory,
  iterationCheckpoints,
  partialResults,
  isRunning,
}) => {
  const { t }  = useTranslation();
  const ct     = useChartTheme();

  const [view,           setView]           = useState<ViewMode>('all');
  const [selectedMethod, setSelectedMethod] = useState<string>('');

  // ── Accumulate history snapshots ──────────────────────────────────────────
  // We keep a ref so updates don't thrash the component; a renderTick state
  // forces a re-render only when a genuinely new checkpoint arrives.
  const historyRef          = useRef<HistoryPoint[]>([]);
  const partialResultsRef   = useRef(partialResults);
  const [renderTick, setRenderTick] = useState(0);

  // Always keep partialResultsRef current (no re-renders from this)
  partialResultsRef.current = partialResults;

  // Accumulate one snapshot per new checkpoint
  useEffect(() => {
    if (iterationCheckpoints.length === 0) {
      historyRef.current = [];
      setRenderTick((n) => n + 1);
      return;
    }

    const latestIter = iterationCheckpoints[iterationCheckpoints.length - 1];
    const last       = historyRef.current[historyRef.current.length - 1];
    if (last?.iter === latestIter) return;   // already recorded this checkpoint

    const pr = partialResultsRef.current;

    // "All methods" aggregation: max win rate per candidate across all methods
    const allMethods: Record<string, number> = {};
    const byMethod:   Record<string, Record<string, number>> = {};

    for (const [method, stats] of Object.entries(pr)) {
      byMethod[method] = { ...stats.winner_distribution };
      for (const [cand, pct] of Object.entries(stats.winner_distribution)) {
        allMethods[cand] = Math.max(allMethods[cand] ?? 0, pct);
      }
    }

    historyRef.current = [...historyRef.current, { iter: latestIter, allMethods, byMethod }];
    setRenderTick((n) => n + 1);
  }, [iterationCheckpoints.length]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Derive candidates + methods ───────────────────────────────────────────
  const candidates = useMemo(() => {
    const names = new Set<string>();
    for (const stats of Object.values(partialResults)) {
      for (const name of Object.keys(stats.winner_distribution)) names.add(name);
    }
    return [...names];
  }, [partialResults]);

  const methods = useMemo(() => Object.keys(partialResults).sort(), [partialResults]);

  // Auto-select first method when methods become available
  useEffect(() => {
    if (!selectedMethod && methods.length > 0) setSelectedMethod(methods[0]);
  }, [methods, selectedMethod]);

  // ── Build chart data ──────────────────────────────────────────────────────
  const chartData = useMemo(() => {
    // eslint-disable-next-line @typescript-eslint/no-unused-expressions
    renderTick; // depend on renderTick to recompute when history grows

    if (view === 'all') {
      return historyRef.current.map((p) => ({
        iter: p.iter,
        ...Object.fromEntries(candidates.map((c) => [c, Math.round((p.allMethods[c] ?? 0) * 100)])),
      }));
    } else {
      return historyRef.current.map((p) => ({
        iter: p.iter,
        ...Object.fromEntries(candidates.map((c) => [c, Math.round((p.byMethod[selectedMethod]?.[c] ?? 0) * 100)])),
      }));
    }
  }, [renderTick, view, candidates, selectedMethod]);

  // ── Final winner ──────────────────────────────────────────────────────────
  const finalWinner = useMemo(() => {
    if (isRunning || historyRef.current.length === 0) return null;
    const last = historyRef.current[historyRef.current.length - 1];
    if (view === 'all') {
      return candidates.reduce((best, c) =>
        (last.allMethods[c] ?? 0) > (last.allMethods[best] ?? 0) ? c : best,
        candidates[0] ?? ''
      );
    } else {
      return partialResults[selectedMethod]?.most_common_winner ?? null;
    }
  }, [isRunning, view, candidates, partialResults, selectedMethod, renderTick]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Don't render until we have data ──────────────────────────────────────
  if (iterationCheckpoints.length === 0 || candidates.length === 0) return null;

  return (
    <Card className="mb-4">
      <Card.Header className="d-flex align-items-center justify-content-between flex-wrap gap-2 py-2">
        <div>
          <strong style={{ fontSize: '0.88rem' }}>{t('simulation.raceTitle')}</strong>
          <div className="text-muted" style={{ fontSize: '0.75rem' }}>{t('simulation.raceDesc')}</div>
        </div>
        <div className="d-flex align-items-center gap-2 flex-wrap">
          {/* View toggle */}
          <div className="d-flex gap-1">
            <Form.Check
              type="radio"
              id="race-view-all"
              name="race-view"
              label={<span style={{ fontSize: '0.78rem' }}>{t('simulation.raceAllMethods')}</span>}
              checked={view === 'all'}
              onChange={() => setView('all')}
            />
            <Form.Check
              type="radio"
              id="race-view-method"
              name="race-view"
              label={<span style={{ fontSize: '0.78rem' }}>{t('simulation.raceOneMethod')}</span>}
              checked={view === 'method'}
              onChange={() => setView('method')}
              className="ms-2"
            />
          </div>

          {/* Method selector (only in method view) */}
          {view === 'method' && (
            <Form.Select
              size="sm"
              value={selectedMethod}
              onChange={(e) => setSelectedMethod(e.target.value)}
              style={{ width: 150 }}
              aria-label={t('simulation.raceOneMethod')}
            >
              {methods.map((m) => <option key={m} value={m}>{m}</option>)}
            </Form.Select>
          )}

          {/* Final winner badge */}
          {finalWinner && !isRunning && (
            <Badge bg="success" style={{ fontSize: '0.72rem' }}>
              🏆 {t('simulation.raceFinalWinner', { winner: finalWinner })}
            </Badge>
          )}
        </div>
      </Card.Header>

      <Card.Body className="p-2">
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={chartData} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} />
            <XAxis
              dataKey="iter"
              tick={{ fontSize: 10, fill: ct.tickFill }}
              label={{ value: t('simulation.convergenceIter'), position: 'insideBottomRight', offset: -4, fontSize: 10, fill: ct.tickFill }}
            />
            <YAxis
              domain={[0, 100]}
              unit="%"
              tick={{ fontSize: 10, fill: ct.tickFill }}
              width={42}
            />
            <Tooltip content={<RaceTooltip t={t} />} />
            <ReferenceLine
              y={50}
              stroke={ct.gridStroke}
              strokeDasharray="4 2"
              strokeWidth={1.5}
              label={{ value: t('simulation.raceMajority'), position: 'insideTopLeft', fontSize: 9, fill: ct.tickFill }}
            />
            {candidates.map((cand, idx) => {
              const color = RACE_COLORS[idx % RACE_COLORS.length];
              return (
                <Area
                  key={cand}
                  type="monotone"
                  dataKey={cand}
                  name={cand}
                  stroke={color}
                  strokeWidth={2}
                  fill={color}
                  fillOpacity={0.08}
                  dot={false}
                  isAnimationActive={false}
                />
              );
            })}
          </AreaChart>
        </ResponsiveContainer>

        {/* Candidate legend */}
        <div className="d-flex gap-3 mt-1 flex-wrap" style={{ fontSize: '0.72rem' }}>
          {candidates.map((cand, idx) => (
            <span key={cand} className="d-flex align-items-center gap-1">
              <span style={{ width: 10, height: 10, borderRadius: 2, background: RACE_COLORS[idx % RACE_COLORS.length], display: 'inline-block' }} />
              {cand}
              {!isRunning && finalWinner === cand && ' 🏆'}
            </span>
          ))}
        </div>
      </Card.Body>
    </Card>
  );
};

export default MonteCarloRaceChart;
