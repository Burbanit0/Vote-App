import React from 'react';
import {
  LIJPHART_REFERENCE,
  lijphartTo01,
  type Band,
} from '../../lib/scorecard';

// DemocracyMap (frontier FA-2) — the Lijphart strip. Real democracies are
// plotted by their (approximate) executives-parties score for CONTEXT; the
// user's three structures are positioned LIVE from their computed consensus
// index over the current electorate. Deliberately 1D: our model speaks to
// Lijphart's first dimension only — plotting the federal-unitary axis we do
// not model would be dishonest.

const W = 480;
const H = 150;
const PAD = 18;
const AXIS_Y = 86;

const STRUCT_COLORS: Record<string, string> = {
  pr: '#16a34a',
  fptp: '#dc2626',
  mmp: '#9333ea',
};

export interface DemocracyMapEntry {
  structure: string;
  label: string;
  index: Band;
}

export interface DemocracyMapProps {
  entries: DemocracyMapEntry[];
  /** Currently selected structure (highlighted). */
  current: string;
}

const x01 = (v: number): number => PAD + v * (W - 2 * PAD);

const DemocracyMap: React.FC<DemocracyMapProps> = ({ entries, current }) => (
  <div data-testid="democracy-map" className="flex flex-col gap-1">
    <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
      Carte des démocraties (axe de Lijphart)
    </p>
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Axe majoritaire–consensus">
      {/* Axis */}
      <line x1={PAD} y1={AXIS_Y} x2={W - PAD} y2={AXIS_Y} stroke="var(--bs-border-color, #ccc)" strokeWidth={1.5} />
      <text x={PAD} y={AXIS_Y + 34} fontSize={10} fill="currentColor" opacity={0.7}>
        ← Majoritaire (décisif, winner-take-all)
      </text>
      <text x={W - PAD} y={AXIS_Y + 34} fontSize={10} fill="currentColor" opacity={0.7} textAnchor="end">
        Consensus (proportionnel, partage) →
      </text>

      {/* Reference countries (context — approximate Lijphart 2012 scores) */}
      <g data-testid="dm-countries" opacity={0.75}>
        {LIJPHART_REFERENCE.map((c, i) => {
          const cx = x01(lijphartTo01(c.score));
          const above = i % 2 === 0;
          return (
            <g key={c.name}>
              <circle cx={cx} cy={AXIS_Y} r={2.5} fill="#64748b" />
              <text
                x={cx}
                y={above ? AXIS_Y - 8 - (i % 4 === 0 ? 10 : 0) : AXIS_Y + 14 + (i % 4 === 1 ? 10 : 0)}
                fontSize={7.5}
                fill="currentColor"
                opacity={0.65}
                textAnchor="middle"
              >
                {c.name}
              </text>
            </g>
          );
        })}
      </g>

      {/* The user's structures — live from the computed consensus index */}
      <g data-testid="dm-structures">
        {entries.map(({ structure, label, index }) => {
          const cx = x01(index.mean);
          const isCurrent = structure === current;
          const color = STRUCT_COLORS[structure] ?? '#2563eb';
          return (
            <g key={structure} data-testid={`dm-${structure}`}>
              {/* Monte-Carlo band */}
              <line
                x1={x01(index.lo)}
                x2={x01(index.hi)}
                y1={AXIS_Y - 26}
                y2={AXIS_Y - 26}
                stroke={color}
                strokeWidth={isCurrent ? 5 : 2.5}
                opacity={0.3}
              />
              {/* Marker */}
              <path
                d={`M ${cx} ${AXIS_Y - 20} l -6 -11 l 12 0 z`}
                fill={color}
                opacity={isCurrent ? 1 : 0.55}
                style={{ transition: 'opacity 300ms ease' }}
              />
              <text
                x={cx}
                y={AXIS_Y - 36}
                fontSize={9}
                fontWeight={isCurrent ? 700 : 400}
                fill={color}
                textAnchor="middle"
              >
                {label}
              </text>
            </g>
          );
        })}
      </g>
    </svg>
    <p className="text-[0.65rem] text-muted-foreground/70">
      Pays : scores « exécutifs-partis » approximatifs (Lijphart 2012), pour situer. Vos
      structures sont positionnées en direct : moyenne de proportionnalité, pluralisme,
      minorités et (1 − gouvernabilité) sur l’électorat courant — convention déclarée,
      1 seule dimension (le fédéralisme n’est pas modélisé).
    </p>
  </div>
);

export default DemocracyMap;
