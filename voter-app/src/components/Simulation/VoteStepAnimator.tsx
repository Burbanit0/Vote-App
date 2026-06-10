import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ButtonGroup } from '@/components/ui/button-group';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { Select } from '@/components/ui/form-controls';
import { Col } from '@/components/ui/grid';
import { Spinner } from '@/components/ui/spinner';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useTranslation } from 'react-i18next';
import { VoteStepsResult, IRVRound, BordaStep } from '../../types';
import { getVoteSteps, VoteStepsParams } from '../../services/simulationCompareApi';
import { useChartTheme } from '../../hooks/useChartTheme';
import { useAnimationBroadcast } from '../../stores/useLabStore';

// ── Palette ───────────────────────────────────────────────────────────────────

const C = {
  blue: '#005CAB',
  orange: '#C8590A',
  green: '#007A33',
  red: '#B71C1C',
  gray: '#6c757d',
};

const CANDIDATE_COLORS = [C.blue, C.orange, C.green, '#7B2D8B', '#9C3A00'];

const SPEEDS: Record<string, number> = { slow: 2000, normal: 1000, fast: 300 };

const ANIMATED_METHODS = ['irv', 'borda', 'plurality', 'schulze', 'approval'] as const;

// ── Helpers ───────────────────────────────────────────────────────────────────

function candidateColor(name: string, all: string[], eliminated?: string | null): string {
  if (name === eliminated) return C.red;
  return CANDIDATE_COLORS[all.indexOf(name) % CANDIDATE_COLORS.length];
}

// ── IRV chart ─────────────────────────────────────────────────────────────────

const IRVChart: React.FC<{
  round: IRVRound;
  allCandidates: string[];
  ct: ReturnType<typeof useChartTheme>;
  t: (k: string) => string;
}> = ({ round, allCandidates, ct, t }) => {
  if (round.winner) {
    return (
      <div className="text-center py-4">
        <div style={{ fontSize: '1.4rem', fontWeight: 700, color: C.green }}>🏆 {round.winner}</div>
        <div className="text-muted-foreground text-sm mt-1">{t('animation.winner')}</div>
      </div>
    );
  }

  const scores = round.scores ?? {};
  const data = Object.entries(scores)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([name, pct]) => ({ name, pct: Math.round(pct * 100) }));

  return (
    <div>
      {round.eliminated && (
        <div className="flex items-center gap-2 mb-2 flex-wrap">
          <Badge variant="danger">
            {round.eliminated} {t('animation.eliminated')}
          </Badge>
          {round.transfers &&
            Object.entries(round.transfers).map(([c, v]) => (
              <Badge key={c} style={{ background: C.green }}>
                {c} +{Math.round(v * 100)}%
              </Badge>
            ))}
        </div>
      )}
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={data} layout="vertical" margin={{ left: 10, right: 40, top: 4, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} horizontal={false} />
          <XAxis
            type="number"
            domain={[0, 100]}
            unit="%"
            tick={{ fontSize: 10, fill: ct.tickFill }}
          />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fontSize: 11, fill: ct.tickFill }}
            width={60}
          />
          <Tooltip contentStyle={ct.tooltipStyle} formatter={(v: number) => [`${v}%`, '']} />
          <Bar dataKey="pct" radius={[0, 4, 4, 0]} isAnimationActive animationDuration={400}>
            <LabelList
              dataKey="pct"
              position="right"
              style={{ fontSize: 11, fill: ct.tickFill }}
              formatter={(v) => `${v}%`}
            />
            {data.map((entry) => (
              <Cell
                key={entry.name}
                fill={candidateColor(entry.name, allCandidates, round.eliminated)}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      {scores && Object.values(scores).some((v) => v > 0.5) && (
        <div className="text-center mt-1" style={{ fontSize: '0.78rem', color: C.green }}>
          ✓ {t('animation.majority')}
        </div>
      )}
    </div>
  );
};

// ── Borda chart ───────────────────────────────────────────────────────────────

const BordaChart: React.FC<{
  step: BordaStep;
  allCandidates: string[];
  winner: string | null;
  isLast: boolean;
  ct: ReturnType<typeof useChartTheme>;
  t: (k: string) => string;
}> = ({ step, allCandidates, winner, isLast, ct, t }) => {
  const maxTally = Math.max(...Object.values(step.tally), 1);
  const data = allCandidates.map((name) => ({
    name,
    points: step.tally[name] ?? 0,
  }));

  return (
    <div>
      <div className="text-muted-foreground text-sm mb-1">
        {t('animation.step')} {step.rank} — {t('animation.borda_adding')}
        <strong>
          {' '}
          {step.points_awarded} {t('animation.borda_pts')}
        </strong>
      </div>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={data} margin={{ top: 16, right: 20, bottom: 20, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} />
          <XAxis dataKey="name" tick={{ fontSize: 11, fill: ct.tickFill }} />
          <YAxis domain={[0, maxTally * 1.1]} tick={{ fontSize: 10, fill: ct.tickFill }} />
          <Tooltip
            contentStyle={ct.tooltipStyle}
            formatter={(v: number) => [v, t('animation.borda_total')]}
          />
          <Bar dataKey="points" radius={[4, 4, 0, 0]} isAnimationActive animationDuration={400}>
            <LabelList
              dataKey="points"
              position="top"
              style={{ fontSize: 10, fill: ct.tickFill }}
            />
            {data.map((entry) => (
              <Cell
                key={entry.name}
                fill={
                  isLast && entry.name === winner
                    ? C.green
                    : candidateColor(entry.name, allCandidates)
                }
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      {isLast && winner && (
        <div className="text-center mt-1" style={{ fontSize: '0.78rem', color: C.green }}>
          🏆 {winner} — {t('animation.winner')}
        </div>
      )}
    </div>
  );
};

// ── Plurality chart ───────────────────────────────────────────────────────────

const PluralityChart: React.FC<{
  firstChoices: Record<string, number>;
  winner: string | null;
  allCandidates: string[];
  ct: ReturnType<typeof useChartTheme>;
  t: (k: string) => string;
}> = ({ firstChoices, winner, allCandidates, ct, t }) => {
  const data = allCandidates.map((name) => ({
    name,
    pct: Math.round((firstChoices[name] ?? 0) * 100),
  }));

  return (
    <div>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={data} layout="vertical" margin={{ left: 10, right: 50, top: 4, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} horizontal={false} />
          <XAxis
            type="number"
            domain={[0, 100]}
            unit="%"
            tick={{ fontSize: 10, fill: ct.tickFill }}
          />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fontSize: 11, fill: ct.tickFill }}
            width={60}
          />
          <Tooltip contentStyle={ct.tooltipStyle} formatter={(v: number) => [`${v}%`, '']} />
          <Bar dataKey="pct" radius={[0, 4, 4, 0]} isAnimationActive animationDuration={600}>
            <LabelList
              dataKey="pct"
              position="right"
              style={{ fontSize: 11 }}
              formatter={(v) => `${v}%`}
            />
            {data.map((entry) => (
              <Cell
                key={entry.name}
                fill={entry.name === winner ? C.green : candidateColor(entry.name, allCandidates)}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      {winner && (
        <div className="text-center mt-1" style={{ fontSize: '0.78rem', color: C.green }}>
          🏆 {winner} — {t('animation.winner')}
        </div>
      )}
    </div>
  );
};

// ── Schulze heatmap ───────────────────────────────────────────────────────────

const SchulzeHeatmap: React.FC<{
  matrix: Record<string, Record<string, number>>;
  candidates: string[];
  title: string;
  winner: string | null;
  showWinner: boolean;
}> = ({ matrix, candidates, title, winner, showWinner }) => {
  const cell = (v: number) => {
    const intensity = Math.round(v * 100);
    const bg =
      v > 0.5 ? `rgba(0,122,51,${0.15 + v * 0.5})` : `rgba(183,28,28,${0.1 + (1 - v) * 0.35})`;
    return { bg, text: `${intensity}%` };
  };

  const CELL_W = Math.min(72, Math.floor(320 / (candidates.length + 1)));

  return (
    <div>
      <div className="text-muted-foreground text-sm mb-1 font-semibold">{title}</div>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ borderCollapse: 'collapse', fontSize: 11 }}>
          <thead>
            <tr>
              <th style={{ width: CELL_W, padding: '3px 6px' }} />
              {candidates.map((c) => (
                <th
                  key={c}
                  style={{
                    width: CELL_W,
                    padding: '3px 6px',
                    textAlign: 'center',
                    color: showWinner && c === winner ? C.green : undefined,
                    fontWeight: showWinner && c === winner ? 700 : 400,
                  }}
                >
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {candidates.map((row) => (
              <tr key={row}>
                <td
                  style={{
                    padding: '3px 6px',
                    fontWeight: 600,
                    color: showWinner && row === winner ? C.green : undefined,
                  }}
                >
                  {row}
                </td>
                {candidates.map((col) => {
                  if (row === col)
                    return (
                      <td
                        key={col}
                        style={{
                          padding: '3px 6px',
                          textAlign: 'center',
                          background: '#f0f0f0',
                          color: '#999',
                        }}
                      >
                        —
                      </td>
                    );
                  const { bg, text } = cell(matrix[row]?.[col] ?? 0);
                  return (
                    <td
                      key={col}
                      title={`${row} vs ${col}`}
                      style={{
                        padding: '3px 6px',
                        textAlign: 'center',
                        background: bg,
                        border: '1px solid rgba(0,0,0,0.06)',
                        borderRadius: 3,
                      }}
                    >
                      {text}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// ── Approval chart ────────────────────────────────────────────────────────────

const ApprovalChart: React.FC<{
  scores: Record<string, number>;
  threshold: number;
  winner: string | null;
  allCandidates: string[];
  animated: boolean;
  ct: ReturnType<typeof useChartTheme>;
  t: (k: string) => string;
}> = ({ scores, threshold, winner, allCandidates, animated, ct, t }) => {
  const data = allCandidates.map((name) => ({
    name,
    pct: Math.round((scores[name] ?? 0) * 100),
    approved: (scores[name] ?? 0) >= threshold,
  }));
  const thresholdPct = Math.round(threshold * 100);

  return (
    <div>
      <div className="text-muted-foreground text-sm mb-1">
        {t('animation.threshold')}: <strong>{thresholdPct}%</strong>
      </div>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={data} layout="vertical" margin={{ left: 10, right: 50, top: 4, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={ct.gridStroke} horizontal={false} />
          <XAxis
            type="number"
            domain={[0, 100]}
            unit="%"
            tick={{ fontSize: 10, fill: ct.tickFill }}
            ticks={[0, 25, 50, 75, 100]}
          />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fontSize: 11, fill: ct.tickFill }}
            width={60}
          />
          <Tooltip
            contentStyle={ct.tooltipStyle}
            formatter={(v: number) => [`${v}%`, t('animation.approval_rate')]}
          />
          <Bar
            dataKey="pct"
            radius={[0, 4, 4, 0]}
            isAnimationActive={animated}
            animationDuration={800}
          >
            <LabelList
              dataKey="pct"
              position="right"
              style={{ fontSize: 11 }}
              formatter={(v) => `${v}%`}
            />
            {data.map((entry) => (
              <Cell key={entry.name} fill={entry.approved ? C.green : C.red} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      {/* Threshold legend */}
      <div className="flex gap-3 mt-1 flex-wrap" style={{ fontSize: '0.75rem' }}>
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
          {t('animation.approved')}
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
          {t('animation.not_approved')}
        </span>
      </div>
      {winner && (
        <div className="text-center mt-1" style={{ fontSize: '0.78rem', color: C.green }}>
          🏆 {winner} — {t('animation.winner')}
        </div>
      )}
    </div>
  );
};

// ── Main component ────────────────────────────────────────────────────────────

interface Props {
  defaultCandidates?: string[];
  // Full candidate configs (with positions) — when provided, the animation
  // uses the SAME spatial setup as the main election simulation, so winners
  // under the same method match across tabs.
  candidateConfigs?: Array<{ name: string; x: number; y: number }>;
  numVoters?: number;
  ideology?: string;
  seed?: number;
}

const VoteStepAnimator: React.FC<Props> = ({
  defaultCandidates,
  candidateConfigs,
  numVoters = 100,
  ideology = 'random',
  seed = 42,
}) => {
  const { t } = useTranslation();
  const ct = useChartTheme();
  const { publish: publishFrame, clear: clearFrame } = useAnimationBroadcast();

  const [method, setMethod] = useState<(typeof ANIMATED_METHODS)[number]>('irv');
  const [speed, setSpeed] = useState<'slow' | 'normal' | 'fast'>('normal');
  const [stepData, setStepData] = useState<VoteStepsResult | null>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // For approval: animate on first reveal
  const [approvalAnimated, setApprovalAnimated] = useState(false);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const candidates = defaultCandidates?.filter(Boolean).slice(0, 8) ?? ['Alice', 'Bob', 'Charlie'];
  // Build payload candidates — use full configs when available
  const apiCandidates: VoteStepsParams['candidates'] = candidateConfigs?.length
    ? candidateConfigs.slice(0, 8)
    : candidates;

  // ── Total steps per method
  const totalSteps = (() => {
    if (!stepData) return 1;
    switch (stepData.method) {
      case 'irv':
        return stepData.rounds.length;
      case 'borda':
        return stepData.steps.length;
      case 'plurality':
        return 1;
      case 'schulze':
        return 2; // duel → path
      case 'approval':
        return 1;
    }
  })();

  // ── Fetch data
  const fetchSteps = useCallback(
    async (m: string, cands: VoteStepsParams['candidates']) => {
      if (cands.length < 2) return;
      setLoading(true);
      setError(null);
      setCurrentStep(0);
      setPlaying(false);
      setApprovalAnimated(false);
      if (intervalRef.current) clearInterval(intervalRef.current);
      try {
        const data = await getVoteSteps({
          method: m,
          num_voters: numVoters,
          candidates: cands,
          ideology,
          seed,
        });
        setStepData(data);
      } catch {
        setError(t('animation.error'));
      } finally {
        setLoading(false);
      }
    },
    [t, numVoters, ideology, seed]
  );

  // Re-fetch when method or any input changes. We stringify the API candidates
  // (which may be names or full objects) to get a stable dep.
  const apiCandsKey = JSON.stringify(apiCandidates);
  useEffect(
    () => {
      fetchSteps(method, apiCandidates);
    }, // eslint-disable-next-line
    [method, apiCandsKey, numVoters, ideology, seed]
  );

  // Clear central-view broadcast when the animator unmounts (user switches tab)
  useEffect(
    () => () => {
      clearFrame();
    },
    [clearFrame]
  );

  // Reveal approval animation on first show
  useEffect(() => {
    // Broadcast current frame to the central view (so the main matrix and
    // map can highlight the active method/round/eliminated candidate).
    if (stepData) {
      let eliminated: string | null | undefined = null;
      let currentWinner: string | null | undefined = null;
      let isFinal = false;
      let eliminatedSet: string[] = [];
      let transfers: Record<string, number> | undefined;

      switch (stepData.method) {
        case 'irv': {
          // Accumulate every candidate eliminated up to and including the
          // current round, so the central map can grey them out cumulatively
          // (rd.eliminated may contain "Bob + Carol" when there's a tie).
          for (let i = 0; i <= currentStep; i++) {
            const r = stepData.rounds[i];
            if (r && 'eliminated' in r && r.eliminated) {
              for (const name of r.eliminated.split(' + ')) {
                const trimmed = name.trim();
                if (trimmed) eliminatedSet.push(trimmed);
              }
            }
          }
          const rd = stepData.rounds[currentStep];
          if (rd) {
            if ('winner' in rd && rd.winner) {
              currentWinner = rd.winner;
              isFinal = true;
            } else if ('eliminated' in rd) {
              eliminated = rd.eliminated ?? null;
              if (rd.transfers) transfers = rd.transfers;
            }
          }
          break;
        }
        case 'plurality':
        case 'approval':
        case 'schulze':
        case 'borda':
          if (currentStep === totalSteps - 1) {
            currentWinner = stepData.winner ?? null;
            isFinal = true;
          }
          break;
      }

      publishFrame({
        method: stepData.method,
        step: currentStep + 1,
        totalSteps,
        eliminated,
        eliminatedSet,
        transfers,
        currentWinner,
        final: isFinal,
      });
    }

    if (stepData?.method === 'approval' && currentStep === 0 && !approvalAnimated) {
      setTimeout(() => setApprovalAnimated(true), 100);
    }
  }, [stepData, currentStep, approvalAnimated]);

  // ── Auto-play interval
  useEffect(() => {
    if (!playing) {
      if (intervalRef.current) clearInterval(intervalRef.current);
      return;
    }
    intervalRef.current = setInterval(() => {
      setCurrentStep((s) => {
        if (s >= totalSteps - 1) {
          setPlaying(false);
          return s;
        }
        return s + 1;
      });
    }, SPEEDS[speed]);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [playing, speed, totalSteps]);

  const handleNext = () => {
    setCurrentStep((s) => Math.min(s + 1, totalSteps - 1));
    setPlaying(false);
  };
  const handleRestart = () => {
    setCurrentStep(0);
    setPlaying(false);
    setApprovalAnimated(false);
  };
  const handlePlay = () => {
    if (currentStep >= totalSteps - 1) setCurrentStep(0);
    setPlaying((p) => !p);
  };

  // ── Render current step
  const renderStep = () => {
    if (!stepData) return null;

    if (stepData.method === 'irv') {
      const round = stepData.rounds[currentStep];
      if (!round) return null;
      return <IRVChart round={round} allCandidates={candidates} ct={ct} t={t} />;
    }

    if (stepData.method === 'borda') {
      const step = stepData.steps[currentStep];
      if (!step) return null;
      return (
        <BordaChart
          step={step}
          allCandidates={candidates}
          winner={stepData.winner}
          isLast={currentStep === stepData.steps.length - 1}
          ct={ct}
          t={t}
        />
      );
    }

    if (stepData.method === 'plurality') {
      return (
        <PluralityChart
          firstChoices={stepData.first_choices}
          winner={stepData.winner}
          allCandidates={candidates}
          ct={ct}
          t={t}
        />
      );
    }

    if (stepData.method === 'schulze') {
      const isDuel = currentStep === 0;
      return (
        <div>
          <SchulzeHeatmap
            matrix={isDuel ? stepData.duel_matrix : stepData.path_matrix}
            candidates={candidates}
            title={isDuel ? t('animation.schulze_duels') : t('animation.schulze_paths')}
            winner={stepData.winner}
            showWinner={!isDuel}
          />
          {!isDuel && stepData.winner && (
            <div className="text-center mt-2" style={{ fontSize: '0.78rem', color: C.green }}>
              🏆 {stepData.winner} — {t('animation.winner')}
            </div>
          )}
        </div>
      );
    }

    if (stepData.method === 'approval') {
      return (
        <ApprovalChart
          scores={stepData.approval_scores}
          threshold={stepData.threshold_used}
          winner={stepData.winner}
          allCandidates={candidates}
          animated={approvalAnimated}
          ct={ct}
          t={t}
        />
      );
    }

    return null;
  };

  // ── Step label
  const stepLabel = (() => {
    if (!stepData) return '';
    if (stepData.method === 'irv')
      return `${t('animation.round')} ${currentStep + 1} / ${totalSteps}`;
    if (stepData.method === 'borda')
      return `${t('animation.step')} ${currentStep + 1} / ${totalSteps}`;
    if (stepData.method === 'schulze')
      return currentStep === 0 ? t('animation.schulze_duels') : t('animation.schulze_paths');
    return '';
  })();

  return (
    <Card>
      <CardHeader className="block space-y-0 border-b border-border px-4 py-2 flex items-center justify-between flex-wrap gap-2 py-2">
        <strong style={{ fontSize: '0.9rem' }}>{t('animation.title')}</strong>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Method select */}
          <Select
            size="sm"
            value={method}
            style={{ width: 140 }}
            onChange={(e) => setMethod(e.target.value as (typeof ANIMATED_METHODS)[number])}
          >
            {ANIMATED_METHODS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </Select>

          {/* Speed */}
          <Select
            size="sm"
            value={speed}
            style={{ width: 110 }}
            onChange={(e) => setSpeed(e.target.value as 'slow' | 'normal' | 'fast')}
          >
            <option value="slow">{t('animation.slow')}</option>
            <option value="normal">{t('animation.normal')}</option>
            <option value="fast">{t('animation.fast')}</option>
          </Select>

          {/* Controls */}
          <ButtonGroup size="sm">
            <Button
              variant={playing ? 'primary' : 'outline-primary'}
              onClick={handlePlay}
              disabled={loading || !stepData}
            >
              {playing ? '⏸' : '▶'} {playing ? t('animation.pause') : t('animation.play')}
            </Button>
            <Button
              variant="outline-secondary"
              onClick={handleNext}
              disabled={loading || !stepData || currentStep >= totalSteps - 1}
            >
              → {t('animation.next')}
            </Button>
            <Button
              variant="outline-secondary"
              onClick={handleRestart}
              disabled={loading || !stepData}
            >
              ↺ {t('animation.restart')}
            </Button>
          </ButtonGroup>

          {/* Step counter */}
          {stepLabel && <span className="text-muted-foreground text-sm">{stepLabel}</span>}
        </div>
      </CardHeader>

      <CardBody style={{ minHeight: 220 }}>
        {loading && (
          <div className="flex items-center justify-center py-5">
            <Spinner size="sm" className="me-2" />
            <span className="text-muted-foreground text-sm">{t('animation.loading')}</span>
          </div>
        )}
        {error && <div className="text-[#dc3545] text-sm">{error}</div>}
        {!loading && !error && renderStep()}
      </CardBody>
    </Card>
  );
};

export default VoteStepAnimator;
