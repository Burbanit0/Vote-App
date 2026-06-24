import React from 'react';
import { cn } from '@/lib/utils';
import { RULE_LABELS, type NamedPt, type Rule } from '../../lib/playgroundVoting';
import { LEADER_RULES } from '../../lib/scorecard';
import { medianPoint } from '../../lib/playgroundDynamics';
import {
  buildBaseVoters,
  trajectory,
  metricsAt,
  driftedAt,
  roundStops,
  type TimelineParams,
} from '../../lib/campaignTimeline';
import { CAMPAIGN_SCENARIOS, DEFAULT_SCENARIO } from '../../lib/campaignScenarios';
import CampaignMap from './CampaignMap';
import Instrument from '../ui/instrument';
import type { ElectionConfig, PlaygroundState } from '../../stores/useElectionStore';

// CampaignTimeline — the /campagne instrument. A scenario rail on the left; a
// console in the middle stacking the value-of-the-result TRAJECTORY (the hero —
// its winner ribbon is the signature, a colour change is a bascule) over a row of
// the ideology MAP (candidate drift) + the live readout; one timeline transport
// underneath drives everything.
//
// Picking a scenario swaps the drift model fed to the shared metrics; scrubbing
// (or ▶ playing) moves both graphs. Pure + client-side, instant, sandbox.

const PALETTE = [
  '#4e79a7',
  '#f28e2b',
  '#e15759',
  '#76b7b2',
  '#59a14f',
  '#edc948',
  '#b07aa1',
  '#ff9da7',
];

interface Props {
  config: ElectionConfig;
  playground: PlaygroundState;
  /** Explicit write-back (Q3): pin the current positions into the playground. */
  onPin?: (candidates: NamedPt[]) => void;
}

const STEPS = 30;

const CampaignTimeline: React.FC<Props> = ({ config, playground, onPin }) => {
  const [scenario, setScenario] = React.useState(DEFAULT_SCENARIO);
  const [rule, setRule] = React.useState<Rule>('plurality');
  const [t, setT] = React.useState(0);
  const [rounds, setRounds] = React.useState(4);
  const [strength, setStrength] = React.useState(0.6);
  const [playing, setPlaying] = React.useState(false);
  const [pinned, setPinned] = React.useState(false);

  const dims = playground.space.dims;
  const numDays = config.campaign?.num_days ?? 30;

  const params: TimelineParams = React.useMemo(
    () => ({
      rule,
      dims,
      turnout: { model: playground.turnout.model, intensity: playground.turnout.intensity },
      strength,
      numDays,
      drift: scenario.drift,
    }),
    [
      rule,
      dims,
      playground.turnout.model,
      playground.turnout.intensity,
      strength,
      numDays,
      scenario,
    ]
  );

  const baseVoters = React.useMemo(() => buildBaseVoters(config, playground), [config, playground]);
  const target = React.useMemo(() => medianPoint(baseVoters), [baseVoters]);

  const traj = React.useMemo(
    () => trajectory(baseVoters, config.candidates, params, STEPS),
    [baseVoters, config.candidates, params]
  );
  const startWinnerIdx = traj[0]?.winnerIdx ?? -1;
  const j0Winner = traj[0]?.winner ?? null;

  const current = React.useMemo(
    () => metricsAt(baseVoters, config.candidates, target, t, params, startWinnerIdx),
    [baseVoters, config.candidates, target, t, params, startWinnerIdx]
  );
  const drifted = React.useMemo(
    () => driftedAt(config.candidates, target, t, params),
    [config.candidates, target, t, params]
  );

  const stops = React.useMemo(() => roundStops(rounds), [rounds]);
  const activeStop = stops.findIndex((s) => Math.abs(s - t) < 1e-6);
  const colorFor = (name: string | null): string => {
    if (!name) return '#9ca3af';
    const i = config.candidates.findIndex((c) => c.name === name);
    return i >= 0 ? PALETTE[i % PALETTE.length] : '#9ca3af';
  };

  const stepRound = (dir: -1 | 1) => {
    let idx = activeStop;
    if (idx < 0) {
      idx = 0;
      let best = Infinity;
      stops.forEach((s, i) => {
        const d = Math.abs(s - t);
        if (d < best) {
          best = d;
          idx = i;
        }
      });
    }
    setT(stops[Math.max(0, Math.min(stops.length - 1, idx + dir))]);
  };

  // Any move on the timeline invalidates the "pinned" confirmation.
  React.useEffect(() => setPinned(false), [t]);

  // ▶ Play: sweep J0→J-end. Respect reduced motion by jumping to the end.
  const reduceMotion =
    typeof window !== 'undefined' &&
    !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
  React.useEffect(() => {
    if (!playing) return;
    if (reduceMotion) {
      setT(1);
      setPlaying(false);
      return;
    }
    const id = window.setInterval(() => {
      setT((prev) => {
        const next = Math.round((prev + 0.02) * 100) / 100;
        if (next >= 1) {
          setPlaying(false);
          return 1;
        }
        return next;
      });
    }, 50);
    return () => window.clearInterval(id);
  }, [playing, reduceMotion]);

  // ── SVG trajectory geometry ──
  const W = 320;
  const H = 110;
  const padX = 4;
  const lineTop = 6;
  const bandH = 16;
  const lineH = H - lineTop - bandH - 8;
  const xAt = (tt: number) => padX + tt * (W - 2 * padX);
  const yAt = (v: number) => lineTop + (1 - Math.max(0, Math.min(1, v))) * lineH;
  const poly = (sel: (m: (typeof traj)[number]) => number) =>
    traj.map((m) => `${xAt(m.t).toFixed(1)},${yAt(sel(m)).toFixed(1)}`).join(' ');
  const congruenceLine = poly((m) => m.congruence);
  const optimalityLine = poly((m) => 1 - m.regret);
  // Flip points: where the winner changes from the previous sample.
  const flips = traj.filter((m, i) => i > 0 && m.winner !== traj[i - 1].winner).map((m) => m.t);

  return (
    <div className="flex flex-col gap-3" data-testid="campaign-timeline">
      {/* ── Thesis (the hero: a result is provisional) ── */}
      <div className="flex flex-col gap-0.5">
        <p className="text-lg font-semibold tracking-tight sm:text-xl">
          Au <span className="text-muted-foreground">J0</span>,{' '}
          {j0Winner ? (
            <span style={{ color: colorFor(j0Winner) }}>{j0Winner}</span>
          ) : (
            <span>—</span>
          )}{' '}
          l’emporte. En campagne, le résultat peut{' '}
          <span className="underline decoration-2 underline-offset-2">bouger</span>.
        </p>
        <p className="text-xs text-muted-foreground">
          Choisissez un scénario, puis avancez le temps pour voir si le vainqueur tient.
        </p>
      </div>

      <div className="grid gap-3 lg:grid-cols-[15rem_1fr]">
        {/* ── Rail: scenario + knobs ── */}
        <div className="flex flex-col gap-3">
          <div
            className="flex flex-col gap-1"
            role="radiogroup"
            aria-label="Scénario de campagne"
            data-testid="timeline-scenario"
          >
            <span className="text-xs font-medium text-muted-foreground">Scénario</span>
            {CAMPAIGN_SCENARIOS.map((sc) => (
              <button
                key={sc.id}
                type="button"
                role="radio"
                aria-checked={sc.id === scenario.id}
                data-testid={`scenario-${sc.id}`}
                onClick={() => setScenario(sc)}
                className={cn(
                  'rounded border px-2 py-1 text-left text-xs transition-colors',
                  sc.id === scenario.id
                    ? 'border-primary bg-primary/10 text-primary'
                    : 'border-border hover:bg-muted'
                )}
              >
                <div className="font-medium">{sc.label}</div>
                <div className="text-[0.65rem] text-muted-foreground">{sc.blurb}</div>
              </button>
            ))}
          </div>

          <label className="flex items-center justify-between gap-2 text-sm">
            <span className="text-muted-foreground">Méthode</span>
            <select
              data-testid="timeline-rule"
              className="rounded border border-border bg-background px-2 py-1 text-sm"
              value={rule}
              onChange={(e) => setRule(e.target.value as Rule)}
            >
              {LEADER_RULES.map((r) => (
                <option key={r} value={r}>
                  {RULE_LABELS[r]}
                </option>
              ))}
            </select>
          </label>
          <label className="flex items-center justify-between gap-2 text-sm">
            <span className="text-muted-foreground">Intensité</span>
            <input
              type="range"
              data-testid="timeline-strength"
              min={0}
              max={1}
              step={0.05}
              value={strength}
              onChange={(e) => setStrength(Number(e.target.value))}
              title="Distance parcourue par les candidats d'ici la fin de campagne."
            />
          </label>
          <label className="flex items-center justify-between gap-2 text-sm">
            <span className="text-muted-foreground">Tours</span>
            <input
              type="number"
              data-testid="timeline-rounds"
              className="w-14 rounded border border-border bg-background px-2 py-1 text-sm"
              min={2}
              max={12}
              value={rounds}
              onChange={(e) => setRounds(Math.max(2, Math.min(12, Number(e.target.value) || 2)))}
            />
          </label>
        </div>

        {/* ── Instrument: the trajectory hero on top, map + live readout below ── */}
        <div className="flex flex-col gap-3" data-testid="campaign-instrument">
          <Instrument
            label="Trajectoire — valeur du résultat"
            readout={`J${current.day} / J${numDays}`}
          >
            <div className="mb-1 flex items-center justify-end gap-2 text-[0.65rem] text-muted-foreground">
              <span className="flex items-center gap-1">
                <span className="inline-block h-1.5 w-3 rounded bg-emerald-500" /> centralité
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-block h-1.5 w-3 rounded bg-sky-500" /> optimalité
              </span>
            </div>
            <svg
              data-testid="campaign-trajectory"
              viewBox={`0 0 ${W} ${H}`}
              className="h-40 w-full sm:h-44"
              preserveAspectRatio="none"
              role="img"
              aria-label="Trajectoire de la valeur du résultat au cours de la campagne"
            >
              {stops.map((s, i) => (
                <line
                  key={i}
                  x1={xAt(s)}
                  x2={xAt(s)}
                  y1={lineTop}
                  y2={lineTop + lineH}
                  stroke="currentColor"
                  strokeWidth={0.5}
                  className="text-border"
                />
              ))}
              {/* metric curves (both "higher is better") */}
              <polyline points={congruenceLine} fill="none" stroke="#10b981" strokeWidth={1.5} />
              <polyline points={optimalityLine} fill="none" stroke="#0ea5e9" strokeWidth={1.5} />
              {/* ── Signature: winner-identity ribbon — a colour change is a bascule ── */}
              {traj.slice(0, -1).map((m, i) => (
                <rect
                  key={i}
                  x={xAt(m.t)}
                  y={H - bandH}
                  width={xAt(traj[i + 1].t) - xAt(m.t) + 0.5}
                  height={bandH}
                  fill={colorFor(m.winner)}
                  opacity={0.9}
                />
              ))}
              {flips.map((ft, i) => (
                <line
                  key={`f${i}`}
                  x1={xAt(ft)}
                  x2={xAt(ft)}
                  y1={H - bandH - 3}
                  y2={H}
                  stroke="currentColor"
                  strokeWidth={1.25}
                  className="text-foreground"
                />
              ))}
              {/* current-time cursor */}
              <line
                x1={xAt(t)}
                x2={xAt(t)}
                y1={lineTop}
                y2={H}
                stroke="currentColor"
                strokeWidth={1}
                className="text-foreground"
              />
            </svg>
            <p className="text-[0.6rem] text-muted-foreground">
              Ruban du bas = vainqueur ; un changement de couleur (trait vertical) est une bascule.
              Optimalité = 1 − regret.
            </p>
          </Instrument>

          {/* ── Map + live readout (the console's bottom row) ── */}
          <div className="grid gap-3 sm:grid-cols-[minmax(0,15rem)_1fr]">
            <Instrument label="Idéologie — dérive" className="w-full max-w-[15rem]">
              <CampaignMap
                voters={baseVoters}
                baseCandidates={config.candidates}
                drifted={drifted}
                target={target}
                winner={current.winner}
                colorFor={colorFor}
              />
            </Instrument>

            <div
              className="grid grid-cols-1 content-start gap-2 sm:grid-cols-2"
              data-testid="timeline-readout"
            >
              <div className="rounded-md border border-border bg-background p-2">
                <div className="text-xs text-muted-foreground">Vainqueur (J{current.day})</div>
                <div className="flex items-center gap-2">
                  <span
                    className="inline-block h-3 w-3 rounded-full"
                    style={{ background: colorFor(current.winner) }}
                  />
                  <span className="font-semibold" data-testid="timeline-winner">
                    {current.winner ?? '—'}
                  </span>
                  {current.flippedFromStart && (
                    <span
                      className="rounded bg-amber-500/15 px-1.5 py-0.5 text-[0.65rem] font-medium text-amber-700 dark:text-amber-400"
                      data-testid="timeline-flip"
                    >
                      bascule depuis J0
                    </span>
                  )}
                </div>
                <div className="mt-1.5" data-testid="timeline-condorcet">
                  {current.condorcetHeld === null ? (
                    <span className="text-[0.7rem] text-muted-foreground">
                      Pas de vainqueur de Condorcet (cycle)
                    </span>
                  ) : current.condorcetHeld ? (
                    <span className="text-[0.7rem] font-medium text-emerald-700 dark:text-emerald-400">
                      ✓ Vainqueur de Condorcet respecté
                    </span>
                  ) : (
                    <span className="text-[0.7rem] font-medium text-rose-700 dark:text-rose-400">
                      ✗ Condorcet non respecté (CW : {current.condorcetWinner})
                    </span>
                  )}
                </div>
              </div>

              <div className="flex flex-col justify-center gap-2 rounded-md border border-border bg-background p-2">
                <Meter label="Regret" value={current.regret} invert testid="timeline-regret" />
                <Meter label="Centralité" value={current.congruence} testid="timeline-congruence" />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Transport: one axis driving both graphs ── */}
      <div className="flex flex-col gap-1">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>
            Jour <strong className="text-foreground">J{current.day}</strong> / J{numDays}
          </span>
          <span>
            {activeStop >= 0 ? (
              <>
                Tour <strong className="text-foreground">{activeStop + 1}</strong> / {rounds}
              </>
            ) : (
              'entre deux tours'
            )}
          </span>
        </div>

        <input
          type="range"
          data-testid="timeline-scrubber"
          className="w-full"
          min={0}
          max={1}
          step={0.01}
          value={t}
          onChange={(e) => {
            setPlaying(false);
            setT(Number(e.target.value));
          }}
          aria-label="Avancement de campagne"
        />

        <div className="relative h-6">
          {stops.map((s, i) => (
            <button
              key={i}
              type="button"
              data-testid={`round-stop-${i}`}
              onClick={() => setT(s)}
              className={cn(
                'absolute top-0 -translate-x-1/2 rounded px-1.5 py-0.5 text-[0.65rem] font-medium',
                i === activeStop
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground hover:bg-muted/70'
              )}
              style={{ left: `${s * 100}%` }}
              title={`Tour ${i + 1}`}
            >
              T{i + 1}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            data-testid="timeline-play"
            className="rounded border border-primary/50 bg-primary/5 px-2 py-0.5 text-xs font-medium text-primary hover:bg-primary/10"
            onClick={() => {
              if (!playing && t >= 1) setT(0);
              setPlaying((p) => !p);
            }}
          >
            {playing ? '⏸ Pause' : '▶ Jouer la campagne'}
          </button>
          <button
            type="button"
            data-testid="round-prev"
            className="rounded border border-border px-2 py-0.5 text-xs hover:bg-muted disabled:opacity-40"
            onClick={() => stepRound(-1)}
            disabled={activeStop === 0}
          >
            ◀ Tour préc.
          </button>
          <button
            type="button"
            data-testid="round-next"
            className="rounded border border-border px-2 py-0.5 text-xs hover:bg-muted disabled:opacity-40"
            onClick={() => stepRound(1)}
            disabled={activeStop === stops.length - 1}
          >
            Tour suiv. ▶
          </button>
          <button
            type="button"
            data-testid="timeline-reset"
            className="rounded border border-border px-2 py-0.5 text-xs hover:bg-muted"
            onClick={() => {
              setPlaying(false);
              setT(0);
            }}
          >
            ↺ J0
          </button>
          {onPin && (
            <button
              type="button"
              data-testid="timeline-pin"
              className="ml-auto rounded border border-primary/50 bg-primary/5 px-2 py-0.5 text-xs font-medium text-primary hover:bg-primary/10"
              onClick={() => {
                onPin(drifted);
                setPinned(true);
              }}
              title="Reporte les positions actuelles des candidats dans le playground comme nouvel état de départ. C'est la seule action qui modifie le playground."
            >
              📌 Épingler dans le playground
            </button>
          )}
        </div>
        {pinned && (
          <p className="text-[0.7rem] text-emerald-700 dark:text-emerald-400" aria-live="polite">
            ✓ Positions reportées dans le playground (J{current.day}).
          </p>
        )}
      </div>
    </div>
  );
};

const Meter: React.FC<{ label: string; value: number; invert?: boolean; testid?: string }> = ({
  label,
  value,
  invert,
  testid,
}) => {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  const good = invert ? 1 - value : value;
  const hue = Math.round(good * 120); // 0 = red, 120 = green
  return (
    <div data-testid={testid}>
      <div className="flex justify-between text-[0.7rem]">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-mono tabular-nums">{pct} %</span>
      </div>
      <div className="h-2 overflow-hidden rounded bg-muted/50">
        <div
          className="h-full rounded"
          style={{ width: `${pct}%`, background: `hsl(${hue} 70% 45%)`, transition: 'width 250ms' }}
        />
      </div>
    </div>
  );
};

export default CampaignTimeline;
