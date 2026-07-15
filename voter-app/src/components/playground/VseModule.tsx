import React from 'react';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib/utils';
import { useVotingLabels } from '../../hooks/useVotingLabels';
import { vseSweep } from '../../lib/playgroundBehavior';
import { COMMUNITY_PALETTE } from '../../lib/playgroundElectorate';
import type { NamedPt, Pt, Rule } from '../../lib/playgroundVoting';

// VseModule — "how much welfare does each method throw away as voters turn
// strategic?" (Voter Satisfaction Efficiency; Quinn 2017, after Merrill 1984).
// Native SVG, per the house split: Recharts is reserved for the heavy lazy panels,
// and this is a small analytical chart. Pure consumer — every number comes from
// lib/playgroundBehavior.ts, which is unit-tested; this file only draws.

const W = 560;
const H = 250;
// Left pad fits the "optimum"/"hasard" reference captions; right pad fits the
// trailing "100 %" tick — both get clipped at the viewBox edge if they are tighter.
const P = { l: 54, r: 24, t: 14, b: 30 };

const colorOf = (i: number): string => COMMUNITY_PALETTE[i % COMMUNITY_PALETTE.length];

export interface VseModuleProps {
  /** Re-draws the SAME electorate composition on a new seed (turnout + mixture included). */
  sampleAtSeed: (seed: number) => Pt[];
  baseSeed: number;
  candidates: NamedPt[];
}

const VseModule: React.FC<VseModuleProps> = ({ sampleAtSeed, baseSeed, candidates }) => {
  const { t } = useTranslation('playground');
  const { ruleLabels } = useVotingLabels();
  const [focus, setFocus] = React.useState<Rule | null>(null);

  const curves = React.useMemo(
    () => vseSweep(sampleAtSeed, baseSeed, candidates),
    [sampleAtSeed, baseSeed, candidates]
  );

  if (candidates.length < 2 || curves.length === 0) {
    return <p className="text-xs text-muted-foreground">{t('vse.need2')}</p>;
  }

  const all = curves.flatMap((c) => c.points.flatMap((p) => [p.vse.lo, p.vse.hi]));
  const yMin = Math.min(0, ...all);
  const yMax = Math.max(1, ...all);
  const span = yMax - yMin || 1;
  const xs = (share: number): number => P.l + share * (W - P.l - P.r);
  const ys = (v: number): number => P.t + (1 - (v - yMin) / span) * (H - P.t - P.b);

  const line = (c: (typeof curves)[number]): string =>
    c.points.map((p, i) => `${i ? 'L' : 'M'} ${xs(p.share)} ${ys(p.vse.mean)}`).join(' ');
  const area = (c: (typeof curves)[number]): string => {
    const up = c.points.map((p, i) => `${i ? 'L' : 'M'} ${xs(p.share)} ${ys(p.vse.hi)}`).join(' ');
    const down = [...c.points]
      .reverse()
      .map((p) => `L ${xs(p.share)} ${ys(p.vse.lo)}`)
      .join(' ');
    return `${up} ${down} Z`;
  };

  // A consensual electorate elects the same (best) candidate whatever the method or
  // the strategy — a flat chart is a real finding, not a bug. Say so rather than
  // leaving the reader staring at seven identical lines.
  const means = curves.flatMap((c) => c.points.map((p) => p.vse.mean));
  const flat = Math.max(...means) - Math.min(...means) < 0.02;

  return (
    <div data-testid="vse-module" className="flex flex-col gap-2">
      <p className="text-[0.7rem] leading-relaxed text-muted-foreground">{t('vse.intro')}</p>

      <svg
        data-testid="vse-chart"
        viewBox={`0 0 ${W} ${H}`}
        className="w-full"
        role="img"
        aria-label={t('vse.aria')}
      >
        {/* reference lines: 1 = utilitarian best, 0 = a candidate drawn at random */}
        {[1, 0].map((v) => (
          <g key={v}>
            <line
              x1={P.l}
              x2={W - P.r}
              y1={ys(v)}
              y2={ys(v)}
              stroke="currentColor"
              strokeWidth={1}
              strokeDasharray={v === 0 ? '3 3' : undefined}
              className="text-border"
            />
            <text
              x={P.l - 5}
              y={ys(v) + 3}
              textAnchor="end"
              className="fill-muted-foreground font-mono text-[9px]"
            >
              {v === 1 ? t('vse.best') : t('vse.random')}
            </text>
          </g>
        ))}

        {/* x axis: strategic share */}
        <line
          x1={P.l}
          x2={W - P.r}
          y1={H - P.b}
          y2={H - P.b}
          stroke="currentColor"
          strokeWidth={1}
          className="text-border"
        />
        {[0, 0.5, 1].map((s) => (
          <text
            key={s}
            x={xs(s)}
            y={H - P.b + 13}
            textAnchor="middle"
            className="fill-muted-foreground font-mono text-[9px]"
          >
            {Math.round(s * 100)} %
          </text>
        ))}
        <text
          x={(P.l + W - P.r) / 2}
          y={H - 2}
          textAnchor="middle"
          className="fill-muted-foreground font-mono text-[9px]"
        >
          {t('vse.xAxis')}
        </text>

        {/* p10–p90 bands (mostly degenerate: with candidates fixed the winner rarely
            changes across re-rolls — they only open where the verdict is fragile) */}
        {curves.map((c, i) => (
          <path
            key={`b-${c.rule}`}
            d={area(c)}
            fill={colorOf(i)}
            opacity={focus === null ? 0.1 : focus === c.rule ? 0.22 : 0.03}
          />
        ))}

        {curves.map((c, i) => (
          <path
            key={c.rule}
            data-testid={`vse-line-${c.rule}`}
            d={line(c)}
            fill="none"
            stroke={colorOf(i)}
            strokeWidth={focus === c.rule ? 3 : 1.8}
            opacity={focus === null || focus === c.rule ? 1 : 0.25}
            strokeLinejoin="round"
          />
        ))}
      </svg>

      {/* legend — hover/click a method to isolate its curve + band */}
      <div className="flex flex-wrap gap-1">
        {curves.map((c, i) => (
          <button
            key={c.rule}
            type="button"
            data-testid={`vse-legend-${c.rule}`}
            onMouseEnter={() => setFocus(c.rule)}
            onMouseLeave={() => setFocus(null)}
            onClick={() => setFocus((f) => (f === c.rule ? null : c.rule))}
            className={cn(
              'flex items-center gap-1.5 rounded-md border px-1.5 py-0.5 text-[0.68rem] transition-colors',
              focus === c.rule
                ? 'border-primary/50 bg-accent/50'
                : 'border-border hover:bg-accent/30'
            )}
          >
            <span
              aria-hidden
              className="h-2 w-2 shrink-0 rounded-full"
              style={{ background: colorOf(i) }}
            />
            {ruleLabels[c.rule]}
            <span className="font-mono text-muted-foreground">
              {c.degradation > 0.05 ? `−${c.degradation.toFixed(2)}` : '—'}
            </span>
          </button>
        ))}
      </div>

      {flat ? (
        <p data-testid="vse-flat" className="text-[0.7rem] leading-relaxed text-muted-foreground">
          {t('vse.flat')}
        </p>
      ) : (
        <p className="text-[0.7rem] leading-relaxed text-muted-foreground">{t('vse.readout')}</p>
      )}
      <p className="text-[0.68rem] leading-relaxed text-muted-foreground/80">
        {t('vse.convention')}
      </p>
    </div>
  );
};

export default VseModule;
