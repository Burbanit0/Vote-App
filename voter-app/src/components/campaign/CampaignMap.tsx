import React from 'react';
import type { NamedPt, Pt } from '../../lib/playgroundVoting';

// CampaignMap — the spatial half of the /campagne instrument: the ideology plane
// with the voter cloud, the median voter, and each candidate's drift TRAIL from
// its J0 position to where the active scenario has moved it at the current
// instant. A small dedicated SVG (not the playground's heavy LeaderCanvas) — its
// one job is to make the motion visible.

const SIZE = 200;
const toSvg = (v: number): number => ((Math.max(-1, Math.min(1, v)) + 1) / 2) * SIZE;

interface Props {
  voters: Pt[];
  baseCandidates: NamedPt[];
  drifted: NamedPt[];
  target: Pt;
  winner: string | null;
  colorFor: (name: string | null) => string;
}

const CampaignMap: React.FC<Props> = ({
  voters,
  baseCandidates,
  drifted,
  target,
  winner,
  colorFor,
}) => (
  <svg
    data-testid="campaign-map"
    viewBox={`0 0 ${SIZE} ${SIZE}`}
    className="aspect-square w-full"
    role="img"
    aria-label="Carte idéologique — les candidats dérivent au cours de la campagne"
  >
    {/* axes */}
    <line
      x1={SIZE / 2}
      y1={0}
      x2={SIZE / 2}
      y2={SIZE}
      className="text-border"
      stroke="currentColor"
      strokeWidth={0.5}
    />
    <line
      x1={0}
      y1={SIZE / 2}
      x2={SIZE}
      y2={SIZE / 2}
      className="text-border"
      stroke="currentColor"
      strokeWidth={0.5}
    />

    {/* voter cloud */}
    {voters.map((v, i) => (
      <circle
        key={i}
        cx={toSvg(v.x)}
        cy={toSvg(v.y ?? 0)}
        r={0.9}
        className="text-muted-foreground"
        fill="currentColor"
        opacity={0.35}
      />
    ))}

    {/* median voter */}
    <g className="text-foreground" stroke="currentColor" strokeWidth={1}>
      <line
        x1={toSvg(target.x) - 3}
        y1={toSvg(target.y ?? 0)}
        x2={toSvg(target.x) + 3}
        y2={toSvg(target.y ?? 0)}
      />
      <line
        x1={toSvg(target.x)}
        y1={toSvg(target.y ?? 0) - 3}
        x2={toSvg(target.x)}
        y2={toSvg(target.y ?? 0) + 3}
      />
    </g>

    {/* per-candidate drift trail (J0 → now) + marker */}
    {drifted.map((c, i) => {
      const base = baseCandidates[i] ?? c;
      const col = colorFor(c.name);
      const cx = toSvg(c.x);
      const cy = toSvg(c.y ?? 0);
      const isWinner = c.name === winner;
      return (
        <g key={c.name} data-testid={`map-candidate-${i}`}>
          <line
            x1={toSvg(base.x)}
            y1={toSvg(base.y ?? 0)}
            x2={cx}
            y2={cy}
            stroke={col}
            strokeWidth={1}
            opacity={0.45}
            strokeDasharray="2 2"
          />
          {isWinner && (
            <circle cx={cx} cy={cy} r={6.5} fill="none" stroke={col} strokeWidth={1.5} />
          )}
          <circle cx={cx} cy={cy} r={4} fill={col} style={{ transition: 'cx 250ms, cy 250ms' }} />
          <text x={cx + 6} y={cy + 3} fontSize={7} fill={col} className="font-medium">
            {c.name}
          </text>
        </g>
      );
    })}
  </svg>
);

export default CampaignMap;
