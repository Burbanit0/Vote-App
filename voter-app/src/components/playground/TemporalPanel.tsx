import React, { useMemo, useState } from 'react';
import { Button } from '@/components/ui/button';
import type { ElectionConfig, PlaygroundState } from '../../stores/useElectionStore';
import { runTemporal, type TemporalResult } from '../../services/assemblyApi';
import { PARTY_PALETTE } from './ParliamentCanvas';

// TemporalPanel (frontier FA-3) — democracy as a repeated game. Runs N
// sequential elections (parties adapt, voters attach — stated dynamics) and
// shows the trajectories: party drift trails on the map, ENP and polarization
// over rounds, alternation/congruence readouts, with a round scrubber and an
// optional second structure compared from the same start.

const W = 480;
const MAP_H = 300;
const CHART_H = 70;
const PAD = 24;

const toX = (v: number): number => PAD + ((v + 1) / 2) * (W - 2 * PAD);
const toY = (v: number): number => PAD + ((1 - v) / 2) * (MAP_H - 2 * PAD);

const STRUCTURES: { value: string; label: string }[] = [
  { value: 'pr', label: 'Proportionnelle' },
  { value: 'fptp', label: 'Circonscriptions' },
  { value: 'mmp', label: 'Mixte (MMP)' },
];

export interface TemporalPanelProps {
  config: ElectionConfig;
  playground: PlaygroundState;
}

/** Polyline for one metric over rounds, mapped into the chart box. */
function metricPath(
  values: (number | null)[],
  yMax: number,
  yOffset: number
): string {
  const pts = values
    .map((v, i) => {
      if (v === null) return null;
      const x = PAD + (i / Math.max(1, values.length - 1)) * (W - 2 * PAD);
      const y = yOffset + CHART_H - Math.min(1, v / yMax) * CHART_H;
      return `${x},${y}`;
    })
    .filter(Boolean);
  return pts.length ? `M ${pts.join(' L ')}` : '';
}

const TemporalPanel: React.FC<TemporalPanelProps> = ({ config, playground }) => {
  const [data, setData] = useState<TemporalResult | null>(null);
  const [compareWith, setCompareWith] = useState<string>('none');
  const [compareData, setCompareData] = useState<TemporalResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [scrub, setScrub] = useState(0);

  const run = async () => {
    setLoading(true);
    try {
      const primary = await runTemporal(config, playground);
      setData(primary);
      setScrub(primary.rounds.length - 1);
      if (compareWith !== 'none' && compareWith !== playground.assembly.structure) {
        setCompareData(await runTemporal(config, playground, compareWith));
      } else {
        setCompareData(null);
      }
    } catch {
      setData(null);
      setCompareData(null);
    } finally {
      setLoading(false);
    }
  };

  const partyNames = useMemo(
    () => (data ? data.rounds[0].parties.map((p) => p.name) : []),
    [data]
  );
  const round = data ? data.rounds[Math.min(scrub, data.rounds.length - 1)] : null;
  const enpMax = 8;
  const polMax = 1;

  return (
    <div data-testid="temporal-panel" className="flex flex-col gap-2 rounded-md border border-border p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          ⏳ Démocratie répétée — le long terme
        </span>
        <div className="flex items-center gap-2">
          <select
            data-testid="temporal-compare"
            className="rounded-md border border-input bg-background px-1.5 py-1 text-xs"
            value={compareWith}
            onChange={(e) => setCompareWith(e.target.value)}
            title="Comparer une seconde structure depuis le même point de départ"
          >
            <option value="none">— sans comparaison —</option>
            {STRUCTURES.filter((s) => s.value !== playground.assembly.structure).map((s) => (
              <option key={s.value} value={s.value}>
                vs {s.label}
              </option>
            ))}
          </select>
          <Button data-testid="temporal-run" variant="outline" size="sm" onClick={run} disabled={loading}>
            {loading ? '…' : '▶ 20 cycles'}
          </Button>
        </div>
      </div>
      <p className="text-[0.68rem] text-muted-foreground/70">
        Modèle déclaré : à chaque cycle les partis font un pas vers les voix (ressources ∝
        votes reçus) et les électeurs dérivent vers le parti qu’ils ont voté. Même graine =
        même trajectoire.
      </p>

      {data && round && (
        <>
          {/* ── Trajectory map: party drift trails ── */}
          <svg viewBox={`0 0 ${W} ${MAP_H}`} width="100%" role="img" aria-label="Trajectoires des partis">
            <rect x={PAD} y={PAD} width={W - 2 * PAD} height={MAP_H - 2 * PAD} fill="none" stroke="var(--bs-border-color, #ccc)" />
            <g data-testid="temporal-trails">
              {partyNames.map((name, i) => {
                const trail = data.rounds.map((r) => {
                  const p = r.parties.find((q) => q.name === name);
                  return p ? `${toX(p.x)},${toY(p.y)}` : '';
                });
                const at = round.parties.find((q) => q.name === name);
                return (
                  <g key={name} data-testid={`trail-${i}`}>
                    <polyline
                      points={trail.join(' ')}
                      fill="none"
                      stroke={PARTY_PALETTE[i % PARTY_PALETTE.length]}
                      strokeWidth={1.5}
                      opacity={0.4}
                    />
                    {at && (
                      <circle
                        cx={toX(at.x)}
                        cy={toY(at.y)}
                        r={4 + at.vote_share * 14}
                        fill={PARTY_PALETTE[i % PARTY_PALETTE.length]}
                        opacity={0.9}
                        style={{ transition: 'cx 150ms, cy 150ms, r 150ms' }}
                      />
                    )}
                  </g>
                );
              })}
            </g>
          </svg>

          {/* ── Round scrubber ── */}
          <div className="flex items-center gap-2 text-xs">
            <span className="w-24 shrink-0 tabular-nums text-muted-foreground">
              Cycle {round.round + 1}/{data.rounds.length}
            </span>
            <input
              data-testid="temporal-scrub"
              type="range"
              className="flex-1"
              min={0}
              max={data.rounds.length - 1}
              step={1}
              value={scrub}
              onChange={(e) => setScrub(Number(e.target.value))}
            />
            <span data-testid="temporal-round-winner" className="w-32 truncate text-right text-muted-foreground">
              en tête : <strong>{round.winner}</strong>
            </span>
          </div>

          {/* ── ENP + polarization over rounds ── */}
          <svg viewBox={`0 0 ${W} ${2 * CHART_H + 36}`} width="100%" role="img" aria-label="NEP et polarisation au fil des cycles">
            <text x={PAD} y={10} fontSize={9} fill="currentColor" opacity={0.7}>
              Nombre effectif de partis (voix)
            </text>
            <path
              data-testid="enp-line"
              d={metricPath(data.rounds.map((r) => r.enp_votes), enpMax, 14)}
              fill="none"
              stroke="#2563eb"
              strokeWidth={1.8}
            />
            {compareData && (
              <path
                data-testid="enp-line-compare"
                d={metricPath(compareData.rounds.map((r) => r.enp_votes), enpMax, 14)}
                fill="none"
                stroke="#2563eb"
                strokeWidth={1.5}
                strokeDasharray="4 3"
                opacity={0.7}
              />
            )}
            <text x={PAD} y={CHART_H + 30} fontSize={9} fill="currentColor" opacity={0.7}>
              Polarisation (dispersion pondérée des partis)
            </text>
            <path
              data-testid="polarization-line"
              d={metricPath(data.rounds.map((r) => r.polarization), polMax, CHART_H + 34)}
              fill="none"
              stroke="#dc2626"
              strokeWidth={1.8}
            />
            {compareData && (
              <path
                d={metricPath(compareData.rounds.map((r) => r.polarization), polMax, CHART_H + 34)}
                fill="none"
                stroke="#dc2626"
                strokeWidth={1.5}
                strokeDasharray="4 3"
                opacity={0.7}
              />
            )}
          </svg>

          {/* ── Readouts ── */}
          <div data-testid="temporal-readouts" className="grid grid-cols-3 gap-2 text-center text-xs">
            <div className="rounded-md border border-border px-1 py-1.5" title="Fréquence de changement du parti en tête — l'alternance, condition de la redevabilité.">
              <div className="font-semibold tabular-nums">{Math.round(data.alternation_rate * 100)} %</div>
              <div className="text-muted-foreground">Alternance</div>
            </div>
            <div className="rounded-md border border-border px-1 py-1.5" title="Nombre effectif de partis (voix), du premier au dernier cycle.">
              <div className="font-semibold tabular-nums">
                {data.enp_votes_initial?.toFixed(1)} → {data.enp_votes_final?.toFixed(1)}
              </div>
              <div className="text-muted-foreground">NEP voix</div>
            </div>
            <div className="rounded-md border border-border px-1 py-1.5" title="Écart entre la position de l'assemblée (pondérée par sièges) et l'électeur médian, au cycle affiché.">
              <div className="font-semibold tabular-nums">{round.congruence_gap.toFixed(2)}</div>
              <div className="text-muted-foreground">Écart de congruence</div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default TemporalPanel;
