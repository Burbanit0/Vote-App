import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  fieldWinnerName,
  winRegionGrid,
  randomBallotProbGrid,
  randomBallotShares,
  RULE_LABELS,
  type Dims,
  type NamedPt,
  type Pt,
  type ProbRegion,
  type Rule,
  type WinRegion,
} from '../../lib/playgroundVoting';
import LeaderScene3D from './LeaderScene3D';
import { manipulationField, type ManipKind } from '../../lib/playgroundSincerity';

// Lenses are overlays rendered IN PLACE on the central map, driven by the same
// knobs (rule, drag, scrubber). 'winner' is the default win-region; 'manipulation'
// tints voters by their incentive to vote strategically; 'probability' reads the
// map as the random-ballot lottery. 'criteria' arrives in a later batch — only
// implemented lenses appear in the switch.
export type Lens = 'winner' | 'manipulation' | 'probability' | 'criteria';

const AVAILABLE_LENSES: { id: Lens; label: string }[] = [
  { id: 'winner', label: 'Vainqueur' },
  { id: 'manipulation', label: 'Manipulation' },
  { id: 'probability', label: 'Probabilité' },
];

const PROB_HUE = '#4f46e5';

// Manipulation lens — each voter as a conviction bloc; colour by temptation.
const MANIP_BLOC_SHARE = 0.12;
const MANIP_COLORS: Record<'compromise' | 'burying', string> = {
  compromise: '#f59e0b', // amber — "vote utile"
  burying: '#dc2626', // red — bury the sincere winner
};
const MANIP_SAFE = '#16a34a'; // green — sincere voting is best (conviction wins)

// LeaderCanvas (Lab reshape P2 · dims FA-2bis) — the live single-office viz over
// a 1/2/3-D ideological space. Candidates are draggable; the plane is shaded by
// the win/entry-region overlay. 1-D collapses to a number line (the median-voter
// theorem made literal); 3-D keeps the x–y map for direct manipulation, edits the
// 3rd axis with per-candidate z sliders, and reads the overlay as a z=0 slice.
// All winner math is genuinely N-D (distances include z).

const SVG = 480;
const MARGIN = 28;
const PLOT = SVG - 2 * MARGIN;
const CENTER = SVG / 2;
const GRID_N = 16;
const VOTER_CAP = 160;

const PALETTE = [
  '#2563eb',
  '#dc2626',
  '#16a34a',
  '#9333ea',
  '#ea580c',
  '#0891b2',
  '#ca8a04',
  '#db2777',
];
const ENTRY_COLOR = '#fbbf24';

const toSvg = (v: number, axis: 'x' | 'y'): number =>
  axis === 'x' ? MARGIN + ((v + 1) / 2) * PLOT : MARGIN + ((1 - v) / 2) * PLOT;

function svgToDomain(clientX: number, clientY: number, rect: DOMRect) {
  const sx = ((clientX - rect.left) / rect.width) * SVG;
  const sy = ((clientY - rect.top) / rect.height) * SVG;
  return {
    x: Math.max(-1, Math.min(1, ((sx - MARGIN) / PLOT) * 2 - 1)),
    y: Math.max(-1, Math.min(1, 1 - ((sy - MARGIN) / PLOT) * 2)),
  };
}

const median = (xs: number[]): number => {
  if (!xs.length) return 0;
  const s = [...xs].sort((a, b) => a - b);
  const mid = Math.floor(s.length / 2);
  return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
};

export interface LeaderCanvasProps {
  candidates: NamedPt[];
  voters: Pt[];
  rule: Rule;
  dims: Dims;
  /** Optional per-voter colour (e.g. by community); falls back to neutral grey. */
  voterColors?: string[];
  /** Optional "you" marker (the sincere-vote module): a draggable diamond. */
  youMarker?: Pt | null;
  /** Active overlay on the central map (defaults to the win-region). */
  lens?: Lens;
  onLensChange?: (lens: Lens) => void;
  onMoveYou?: (x: number, y: number) => void;
  onRuleChange: (rule: Rule) => void;
  onMoveCandidate: (index: number, x: number, y: number, z?: number) => void;
}

const LeaderCanvas: React.FC<LeaderCanvasProps> = ({
  candidates,
  voters,
  rule,
  dims,
  voterColors,
  youMarker,
  lens = 'winner',
  onLensChange,
  onMoveYou,
  onRuleChange,
  onMoveCandidate,
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const draggingIdx = useRef<number | null>(null);
  const draggingYou = useRef<boolean>(false);
  const [region, setRegion] = useState<WinRegion | null>(null);
  const [probRegion, setProbRegion] = useState<ProbRegion | null>(null);
  const [manipField, setManipField] = useState<ManipKind[] | null>(null);
  // In 3-D, default to the orbital scene (what the dimension is *for*); the
  // x–y plane stays available for editing + the win-region overlay.
  const [scene3d, setScene3d] = useState(true);
  const show3d = dims === 3 && scene3d;

  // y maps to the plane in 2/3-D, to the centre line in 1-D.
  const cyOf = (p: Pt): number => (dims === 1 ? CENTER : toSvg(p.y, 'y'));

  const gridVoters = useMemo(
    () =>
      voters.length > VOTER_CAP
        ? voters.filter((_, i) => i % Math.ceil(voters.length / VOTER_CAP) === 0)
        : voters,
    [voters]
  );

  // Only the active lens computes (default 'winner' = identical to before — no
  // extra work at first paint). The probability lens reads the random-ballot
  // lottery; the win-region lens reads the current rule.
  useEffect(() => {
    let alive = true;
    const t = setTimeout(() => {
      if (!alive) return;
      if (lens === 'probability') {
        setProbRegion(randomBallotProbGrid(gridVoters, candidates, GRID_N, dims));
      } else if (lens === 'manipulation') {
        setManipField(manipulationField(gridVoters, candidates, rule, MANIP_BLOC_SHARE));
      } else {
        setRegion(winRegionGrid(gridVoters, candidates, rule, GRID_N, dims));
      }
    }, 120);
    return () => {
      alive = false;
      clearTimeout(t);
    };
  }, [gridVoters, candidates, rule, dims, lens]);

  // Manipulation summary (the Gibbard-Satterthwaite boundary, inline): how many
  // voters this rule tempts vs random ballot's guaranteed zero.
  const manipSummary = useMemo(() => {
    if (lens !== 'manipulation' || !manipField || manipField.length === 0) return null;
    const compromise = manipField.filter((k) => k === 'compromise').length;
    const burying = manipField.filter((k) => k === 'burying').length;
    const tempted = compromise + burying;
    return { compromise, burying, rate: tempted / manipField.length };
  }, [lens, manipField]);

  // Current field's lottery (existing candidates' first-preference shares).
  const lotteryShares = useMemo(
    () => (lens === 'probability' ? randomBallotShares(voters, candidates) : null),
    [lens, voters, candidates]
  );

  useEffect(() => {
    const move = (clientX: number, clientY: number) => {
      if (!svgRef.current) return;
      const { x, y } = svgToDomain(clientX, clientY, svgRef.current.getBoundingClientRect());
      if (draggingYou.current) {
        onMoveYou?.(x, dims === 1 ? 0 : y);
        return;
      }
      if (draggingIdx.current === null) return;
      onMoveCandidate(draggingIdx.current, x, dims === 1 ? 0 : y);
    };
    const onMM = (e: MouseEvent) => move(e.clientX, e.clientY);
    const onUp = () => {
      draggingIdx.current = null;
      draggingYou.current = false;
    };
    const onTM = (e: TouchEvent) => {
      if ((draggingIdx.current === null && !draggingYou.current) || !e.touches[0]) return;
      e.preventDefault();
      move(e.touches[0].clientX, e.touches[0].clientY);
    };
    const svg = svgRef.current;
    window.addEventListener('mousemove', onMM);
    window.addEventListener('mouseup', onUp);
    svg?.addEventListener('touchmove', onTM, { passive: false });
    svg?.addEventListener('touchend', onUp);
    return () => {
      window.removeEventListener('mousemove', onMM);
      window.removeEventListener('mouseup', onUp);
      svg?.removeEventListener('touchmove', onTM);
      svg?.removeEventListener('touchend', onUp);
    };
  }, [onMoveCandidate, onMoveYou, dims]);

  const winner = fieldWinnerName(voters, candidates, rule);
  const mx = median(voters.map((v) => v.x));
  const my = median(voters.map((v) => v.y));
  const cellW = PLOT / GRID_N;

  const colorFor = (idx: number): string =>
    idx === candidates.length ? ENTRY_COLOR : PALETTE[idx % PALETTE.length];

  return (
    <div data-testid="leader-canvas" data-dims={dims} className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <label className="flex items-center gap-2 text-sm">
          <span className="text-muted-foreground">Règle</span>
          <select
            data-testid="rule-select"
            className="rounded-md border border-input bg-background px-2 py-1 text-sm"
            value={rule}
            onChange={(e) => onRuleChange(e.target.value as Rule)}
          >
            {(Object.keys(RULE_LABELS) as Rule[]).map((r) => (
              <option key={r} value={r}>
                {RULE_LABELS[r]}
              </option>
            ))}
          </select>
        </label>
        <span data-testid="field-winner" className="text-sm">
          Vainqueur : <strong>{winner ?? '—'}</strong>
        </span>
      </div>

      {/* Lens switch — overlays rendered in place on the same map. */}
      <div
        data-testid="lens-switch"
        role="radiogroup"
        aria-label="Vue de la carte"
        className="flex items-center gap-1 text-xs"
      >
        <span className="text-muted-foreground">Vue</span>
        {AVAILABLE_LENSES.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            role="radio"
            aria-checked={lens === id}
            data-testid={`lens-${id}`}
            className={`rounded border px-2 py-0.5 ${
              lens === id ? 'border-primary text-primary' : 'border-border text-muted-foreground'
            }`}
            onClick={() => onLensChange?.(id)}
          >
            {label}
          </button>
        ))}
      </div>

      {/* 3-D view toggle: orbital scene vs the editable x–y plane. */}
      {dims === 3 && (
        <div className="flex gap-1 text-xs">
          <button
            type="button"
            data-testid="view-3d"
            className={`rounded border px-2 py-0.5 ${scene3d ? 'border-primary text-primary' : 'border-border'}`}
            onClick={() => setScene3d(true)}
          >
            🧊 Vue 3D
          </button>
          <button
            type="button"
            data-testid="view-plane"
            className={`rounded border px-2 py-0.5 ${!scene3d ? 'border-primary text-primary' : 'border-border'}`}
            onClick={() => setScene3d(false)}
          >
            ▦ Plan x–y (édition)
          </button>
        </div>
      )}

      {show3d && <LeaderScene3D voters={voters} candidates={candidates} palette={PALETTE} />}

      <svg
        ref={svgRef}
        viewBox={`0 0 ${SVG} ${SVG}`}
        width="100%"
        role="img"
        aria-label="Carte idéologique — élire un dirigeant"
        className="touch-none select-none rounded-lg bg-card"
        style={{ maxHeight: '70vh', display: show3d ? 'none' : undefined }}
      >
        {/* Win/entry-region overlay (full-height columns in 1-D) */}
        {lens === 'winner' && (
          <g data-testid="winregion" opacity={0.28}>
            {region &&
              region.cells.map((widx, k) => {
                const cellH = PLOT / region.rows;
                const r = Math.floor(k / region.n);
                const c = k % region.n;
                return (
                  <rect
                    key={k}
                    x={MARGIN + c * cellW}
                    y={MARGIN + r * cellH}
                    width={cellW + 0.5}
                    height={cellH + 0.5}
                    fill={colorFor(widx)}
                  />
                );
              })}
          </g>
        )}

        {/* Probability lens — random-ballot win-probability heatmap of a new
            entrant: opacity ∝ its lottery chance (first-preference basin). */}
        {lens === 'probability' && probRegion && (
          <g data-testid="problens">
            {(() => {
              const maxV = Math.max(...probRegion.cells, 1e-6);
              return probRegion.cells.map((val, k) => {
                const cellH = PLOT / probRegion.rows;
                const r = Math.floor(k / probRegion.n);
                const c = k % probRegion.n;
                return (
                  <rect
                    key={k}
                    x={MARGIN + c * cellW}
                    y={MARGIN + r * cellH}
                    width={cellW + 0.5}
                    height={cellH + 0.5}
                    fill={PROB_HUE}
                    opacity={(val / maxV) * 0.8}
                  />
                );
              });
            })()}
          </g>
        )}

        {/* Plot border + axes */}
        <rect
          x={MARGIN}
          y={MARGIN}
          width={PLOT}
          height={PLOT}
          fill="none"
          stroke="var(--bs-border-color, #ccc)"
        />
        <line
          x1={MARGIN}
          y1={dims === 1 ? CENTER : toSvg(0, 'y')}
          x2={MARGIN + PLOT}
          y2={dims === 1 ? CENTER : toSvg(0, 'y')}
          stroke="var(--bs-border-color, #ddd)"
          strokeDasharray="3 3"
        />
        {dims !== 1 && (
          <line
            x1={toSvg(0, 'x')}
            y1={MARGIN}
            x2={toSvg(0, 'x')}
            y2={MARGIN + PLOT}
            stroke="var(--bs-border-color, #ddd)"
            strokeDasharray="3 3"
          />
        )}

        {/* Voters. In the manipulation lens the sampled cloud is tinted by each
            voter's strategic temptation; otherwise by community (or neutral). */}
        {lens === 'manipulation' && manipField ? (
          <g data-testid="manip-voters">
            {gridVoters.map((v, i) => {
              const kind = manipField[i];
              return (
                <circle
                  key={i}
                  cx={toSvg(v.x, 'x')}
                  cy={cyOf(v)}
                  r={2.6}
                  fill={kind ? MANIP_COLORS[kind] : MANIP_SAFE}
                  opacity={kind ? 0.9 : 0.55}
                />
              );
            })}
          </g>
        ) : (
          <g>
            {voters.map((v, i) => (
              <circle
                key={i}
                cx={toSvg(v.x, 'x')}
                cy={cyOf(v)}
                r={1.6}
                fill={voterColors?.[i] ?? '#64748b'}
                opacity={voterColors ? 0.6 : 0.5}
              />
            ))}
          </g>
        )}

        {/* Median-voter marker */}
        <g data-testid="median-marker">
          <circle
            cx={toSvg(mx, 'x')}
            cy={dims === 1 ? CENTER : toSvg(my, 'y')}
            r={5}
            fill="none"
            stroke="#111827"
            strokeWidth={1.5}
          />
          <line
            x1={toSvg(mx, 'x') - 8}
            y1={dims === 1 ? CENTER : toSvg(my, 'y')}
            x2={toSvg(mx, 'x') + 8}
            y2={dims === 1 ? CENTER : toSvg(my, 'y')}
            stroke="#111827"
            strokeWidth={1}
          />
          {dims !== 1 && (
            <line
              x1={toSvg(mx, 'x')}
              y1={toSvg(my, 'y') - 8}
              x2={toSvg(mx, 'x')}
              y2={toSvg(my, 'y') + 8}
              stroke="#111827"
              strokeWidth={1}
            />
          )}
        </g>

        {/* Draggable candidates (z shown as an outer ring in 3-D) */}
        <g>
          {candidates.map((cand, i) => {
            const cx = toSvg(cand.x, 'x');
            const cy = cyOf(cand);
            const zr = dims === 3 ? 9 + Math.abs(cand.z ?? 0) * 12 : 0;
            return (
              <g
                key={`${cand.name}-${i}`}
                data-testid={`candidate-${i}`}
                style={{ cursor: 'grab' }}
                onMouseDown={(e) => {
                  e.preventDefault();
                  draggingIdx.current = i;
                }}
                onTouchStart={() => {
                  draggingIdx.current = i;
                }}
              >
                {dims === 3 && (cand.z ?? 0) !== 0 && (
                  <circle
                    cx={cx}
                    cy={cy}
                    r={zr}
                    fill="none"
                    stroke={PALETTE[i % PALETTE.length]}
                    strokeWidth={1}
                    strokeDasharray="2 2"
                    opacity={0.7}
                  />
                )}
                <circle
                  cx={cx}
                  cy={cy}
                  r={9}
                  fill={PALETTE[i % PALETTE.length]}
                  stroke="#fff"
                  strokeWidth={2}
                />
                <text
                  x={cx}
                  y={cy - 13}
                  textAnchor="middle"
                  fontSize={11}
                  fontWeight={600}
                  fill="currentColor"
                >
                  {cand.name}
                  {dims === 3 && (cand.z ?? 0) !== 0 ? ` (z ${(cand.z ?? 0).toFixed(1)})` : ''}
                </text>
              </g>
            );
          })}
        </g>

        {/* "You" marker (sincere-vote module) — a draggable diamond. */}
        {youMarker && (
          <g
            data-testid="you-marker"
            style={{ cursor: 'grab' }}
            onMouseDown={(e) => {
              e.preventDefault();
              draggingYou.current = true;
            }}
            onTouchStart={() => {
              draggingYou.current = true;
            }}
          >
            {(() => {
              const cx = toSvg(youMarker.x, 'x');
              const cy = cyOf(youMarker);
              return (
                <>
                  <rect
                    x={cx - 7}
                    y={cy - 7}
                    width={14}
                    height={14}
                    transform={`rotate(45 ${cx} ${cy})`}
                    fill="#0f172a"
                    stroke="#fff"
                    strokeWidth={2}
                  />
                  <text
                    x={cx}
                    y={cy + 20}
                    textAnchor="middle"
                    fontSize={11}
                    fontWeight={700}
                    fill="currentColor"
                  >
                    Vous
                  </text>
                </>
              );
            })()}
          </g>
        )}
      </svg>

      {/* Manipulation lens — strategy legend + the Gibbard-Satterthwaite boundary
          made concrete: this rule's tempted share vs random ballot's zero. */}
      {lens === 'manipulation' && manipSummary && (
        <div
          data-testid="manip-summary"
          className="flex flex-col gap-1 rounded-md border border-border p-2 text-xs"
        >
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <span className="flex items-center gap-1">
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ background: MANIP_COLORS.compromise }}
              />
              Compromis (vote utile)
            </span>
            <span className="flex items-center gap-1">
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ background: MANIP_COLORS.burying }}
              />
              Enterrement
            </span>
            <span className="flex items-center gap-1">
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ background: MANIP_SAFE }}
              />
              Conviction récompensée
            </span>
          </div>
          <p className="text-muted-foreground">
            Sous <strong>{RULE_LABELS[rule]}</strong> :{' '}
            <strong>{Math.round(manipSummary.rate * 100)}%</strong> des électeurs tentés de voter
            stratégiquement ({manipSummary.compromise} compromis · {manipSummary.burying}{' '}
            enterrement). Vote au sort : <strong>0 %</strong> — la seule règle inmanipulable
            (Gibbard 1977). Toute règle ordinale déterministe est manipulable : c’est la frontière
            de Gibbard-Satterthwaite.
          </p>
        </div>
      )}

      {/* Probability lens — the current field's lottery as animated bars. */}
      {lens === 'probability' && lotteryShares && (
        <div
          data-testid="lottery-bars"
          className="flex flex-col gap-1 rounded-md border border-border p-2"
        >
          <span className="text-[0.7rem] font-medium text-muted-foreground">
            Loterie du vote au sort — probabilité de victoire (= part des premières voix)
          </span>
          {candidates.map((c, i) => (
            <div key={i} className="flex items-center gap-2 text-xs">
              <span
                className="w-20 shrink-0 truncate"
                style={{ color: PALETTE[i % PALETTE.length] }}
              >
                {c.name}
              </span>
              <div className="h-2 flex-1 overflow-hidden rounded bg-muted">
                <div
                  className="h-full animate-pulse rounded"
                  style={{
                    width: `${(lotteryShares[i] ?? 0) * 100}%`,
                    background: PALETTE[i % PALETTE.length],
                    transition: 'width 400ms ease',
                  }}
                />
              </div>
              <span className="w-10 text-right tabular-nums text-muted-foreground">
                {Math.round((lotteryShares[i] ?? 0) * 100)}%
              </span>
            </div>
          ))}
        </div>
      )}

      {/* 3-D depth controls — the z axis can't be dragged on a 2-D plane. */}
      {dims === 3 && (
        <div
          data-testid="z-controls"
          className="flex flex-col gap-1 rounded-md border border-border p-2"
        >
          <span className="text-[0.7rem] font-medium text-muted-foreground">
            Axe z (profondeur) — réglé par curseur
          </span>
          {candidates.map((cand, i) => (
            <label key={i} className="flex items-center gap-2 text-xs">
              <span
                className="w-20 shrink-0 truncate"
                style={{ color: PALETTE[i % PALETTE.length] }}
              >
                {cand.name}
              </span>
              <input
                data-testid={`z-slider-${i}`}
                type="range"
                className="flex-1"
                min={-1}
                max={1}
                step={0.05}
                value={cand.z ?? 0}
                onChange={(e) => onMoveCandidate(i, cand.x, cand.y, Number(e.target.value))}
              />
              <span className="w-8 text-right tabular-nums text-muted-foreground">
                {(cand.z ?? 0).toFixed(1)}
              </span>
            </label>
          ))}
        </div>
      )}

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
        {candidates.map((c, i) => (
          <span key={i} className="flex items-center gap-1">
            <span
              className="inline-block h-2.5 w-2.5 rounded-sm"
              style={{ background: PALETTE[i % PALETTE.length] }}
            />
            {c.name}
          </span>
        ))}
        <span className="flex items-center gap-1">
          <span
            className="inline-block h-2.5 w-2.5 rounded-sm"
            style={{ background: ENTRY_COLOR }}
          />
          Zone d’un nouvel entrant
        </span>
      </div>
      <p className="text-xs text-muted-foreground/70">
        {lens === 'manipulation' &&
          'Lentille Manipulation : chaque électeur est traité comme un bloc de conviction ; sa couleur dit si la règle le pousse à voter utile. Glissez un candidat ou changez de règle — les tentations se redessinent. '}
        {lens === 'probability' &&
          'Lentille Probabilité : sous le vote au sort, un bulletin est tiré au hasard — l’intensité montre la chance de victoire d’un nouvel entrant, et chaque bassin devient une probabilité (et non une frontière nette). '}
        {dims === 1 &&
          'Espace à 1 dimension : tout se joue sur un axe — le terrain du théorème de l’électeur médian.'}
        {dims === 2 &&
          'Glissez les candidats. Les zones colorées montrent qui gagnerait si un candidat était placé là — les frontières révèlent les régions vulnérables au vote stratégique.'}
        {dims === 3 &&
          show3d &&
          'Vue 3D orbitale : glissez pour pivoter, les électeurs sont colorés par candidat le plus proche (en 3-D). Basculez en « Plan x–y » pour éditer et voir l’overlay.'}
        {dims === 3 &&
          !show3d &&
          'Plan x–y (réglez z au curseur) ; le calcul du vainqueur est bien en 3-D, mais l’overlay n’est qu’une tranche z=0.'}
      </p>
    </div>
  );
};

export default LeaderCanvas;
