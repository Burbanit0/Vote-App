import React from 'react';
import type { Band } from '../../lib/scorecard';

// Scorecard (Lab reshape P5) — the mode-aware axis read-out. Every number
// carries its Monte-Carlo band: the track shows [p10, p90], the tick is the
// mean. Axes are oriented higher-is-better with stated conventions (tooltips).

export interface ScorecardAxis {
  key: string;
  label: string;
  hint: string;
  band: Band | null;
}

export interface ScorecardProps {
  axes: ScorecardAxis[];
  loading?: boolean;
  /** e.g. "24 ré-échantillonnages" */
  bandNote?: string;
}

const Scorecard: React.FC<ScorecardProps> = ({ axes, loading = false, bandNote }) => (
  <div data-testid="scorecard" className="flex flex-col gap-2.5">
    {axes.map(({ key, label, hint, band }) => (
      <div key={key} data-testid={`axis-${key}`} title={hint}>
        <div className="flex items-center justify-between text-xs">
          <span className="text-muted-foreground">{label}</span>
          <span className="font-semibold tabular-nums">
            {band && !loading ? `${Math.round(band.mean * 100)} %` : '…'}
          </span>
        </div>
        <div className="relative mt-1 h-2 overflow-hidden rounded-full bg-muted/60">
          {band && !loading && (
            <>
              {/* The Monte-Carlo band [p10, p90] */}
              <div
                className="absolute inset-y-0 rounded-full bg-primary/30"
                style={{
                  left: `${band.lo * 100}%`,
                  width: `${Math.max(1.5, (band.hi - band.lo) * 100)}%`,
                  transition: 'left 400ms ease, width 400ms ease',
                }}
              />
              {/* The mean tick */}
              <div
                className="absolute inset-y-0 w-1 rounded bg-primary"
                style={{ left: `calc(${band.mean * 100}% - 2px)`, transition: 'left 400ms ease' }}
              />
            </>
          )}
        </div>
      </div>
    ))}
    {bandNote && (
      <p className="text-[0.7rem] text-muted-foreground/70">
        Bande = p10–p90 sur {bandNote} ; trait = moyenne.
      </p>
    )}
  </div>
);

export default Scorecard;
