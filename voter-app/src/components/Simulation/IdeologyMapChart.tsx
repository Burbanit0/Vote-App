import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Badge, Button, ButtonGroup, Card, Col, Form, ProgressBar, Row, Spinner,
} from 'react-bootstrap';
import IdeologyHeatmap from './IdeologyHeatmap';
import MedianVoterLayer, { MedianVoterLegend } from './MedianVoterLayer';
import { useDragTouch } from '../../hooks/useDragTouch';
import { useTranslation } from 'react-i18next';
import { useAnimationBroadcast } from '../../context/AnimationBroadcastContext';
import { IdeologyMapResult, IdeologyMapVoter } from '../../types';
import { getIdeologyMap, IdeologyMapParams } from '../../services/simulationCompareApi';
import { buildVoronoiPaths } from '../../utils/voronoiRegions';

// ── Constants ─────────────────────────────────────────────────────────────────

const SVG_W      = 480;
const SVG_H      = 480;
const MARGIN     = 40;
const PLOT_W     = SVG_W - 2 * MARGIN;
const PLOT_H     = SVG_H - 2 * MARGIN;

const COLOR_A    = '#005CAB';   // blue  — prefers method A winner
const COLOR_B    = '#C8590A';   // orange — prefers method B winner
const COLOR_LOSE = '#B71C1C';   // red   — "loser" highlight (low utility)

const PARTY_COLORS: Record<string, string> = {
  Green:        '#007A33',
  Liberal:      '#005CAB',
  Conservative: '#C8590A',
  Independent:  '#6c757d',
};

// Palette for Voronoi regions — distinct from voter-dot colors (blue/orange)
const VORONOI_COLORS = [
  '#9C3A00', '#264653', '#7B2D8B', '#005f73',
  '#B71C1C', '#6A0DAD', '#2A9D8F', '#E76F51',
];

const METHODS = [
  'plurality','two_round','borda','approval','irv','coombs','bucklin',
  'minimax','schulze','simple_score','star_voting','median_voting',
  'mean_median_hybrid','variance_based',
];

// ── Coord helpers ─────────────────────────────────────────────────────────────

function domainToSvg(v: number, axis: 'x' | 'y'): number {
  if (axis === 'x') return MARGIN + ((v + 1) / 2) * PLOT_W;
  // Y axis: domain -1 = bottom, +1 = top  →  flip for SVG
  return MARGIN + ((1 - v) / 2) * PLOT_H;
}

function svgToDomain(px: number, py: number, rect: DOMRect) {
  const relX = (px - rect.left) / rect.width;
  const relY = (py - rect.top)  / rect.height;
  const svgX = relX * SVG_W;
  const svgY = relY * SVG_H;
  const x = Math.max(-1, Math.min(1, ((svgX - MARGIN) / PLOT_W) * 2 - 1));
  const y = Math.max(-1, Math.min(1, 1 - ((svgY - MARGIN) / PLOT_H) * 2));
  return { x, y };
}

// ── Tooltip ───────────────────────────────────────────────────────────────────

interface TooltipState {
  voter: IdeologyMapVoter;
  screenX: number;
  screenY: number;
  winnerA: string | null;
  winnerB: string | null;
}

const VoterTooltip: React.FC<{ tip: TooltipState; t: (k: string) => string }> = ({ tip, t }) => (
  <div
    role="tooltip"
    style={{
      position: 'fixed',
      left: tip.screenX + 12,
      top:  tip.screenY - 10,
      background: 'rgba(0,0,0,0.82)',
      color: '#fff',
      padding: '6px 10px',
      borderRadius: 6,
      fontSize: '0.75rem',
      pointerEvents: 'none',
      zIndex: 9000,
      whiteSpace: 'nowrap',
      lineHeight: 1.6,
    }}
  >
    {tip.winnerA && <div>{t('ideologyMap.tooltipA')} {tip.winnerA}: <strong>{tip.voter.utility_winner_a.toFixed(3)}</strong></div>}
    {tip.winnerB && <div>{t('ideologyMap.tooltipB')} {tip.winnerB}: <strong>{tip.voter.utility_winner_b.toFixed(3)}</strong></div>}
  </div>
);

// ── Main component ────────────────────────────────────────────────────────────

interface CandidatePos { name: string; x: number; y: number }

interface Props {
  defaultCandidates?: string[];
  /** Full candidate positions (name + x + y) — when provided, used directly
   *  instead of the auto-placed positions. Required for the LabCentralView
   *  so the map matches the configured scenario (e.g. France 2002). */
  initialCandidatePositions?: Array<{ name: string; x: number; y: number }>;
  defaultNumVoters?:  number;
  defaultIdeology?:   string;
  defaultSeed?:       number;
  /** Embedded in another view (e.g. LabCentralView). When true: hide the
   *  controls column entirely and disable candidate dragging — the parent
   *  page already provides the relevant configuration. */
  embedded?:          boolean;
}

const IdeologyMapChart: React.FC<Props> = ({
  defaultCandidates, initialCandidatePositions, defaultNumVoters, defaultIdeology,
  defaultSeed, embedded = false,
}) => {
  const { t } = useTranslation();

  // ── Controls state (initialized from props when provided)
  const [methodA,      setMethodA]      = useState('plurality');
  const [methodB,      setMethodB]      = useState('schulze');
  const [numVoters,    setNumVoters]    = useState(defaultNumVoters ?? 200);
  const [ideology,     setIdeology]     = useState(defaultIdeology  ?? 'random');
  const [seed,         setSeed]         = useState(defaultSeed      ?? 42);

  // Sync with lab config when it changes externally
  useEffect(() => {
    if (defaultNumVoters !== undefined) setNumVoters(defaultNumVoters);
    if (defaultIdeology  !== undefined) setIdeology(defaultIdeology);
    if (defaultSeed      !== undefined) setSeed(defaultSeed);
  }, [defaultNumVoters, defaultIdeology, defaultSeed]);
  const [showLosers,   setShowLosers]   = useState(false);
  const [showVoronoi,  setShowVoronoi]  = useState(false);
  const [viewMode,     setViewMode]     = useState<'points' | 'heatmap' | 'both'>('points');
  const [showMedian,   setShowMedian]   = useState(false);

  // ── Candidate positions (draggable when not embedded)
  // Priority: real positions from initialCandidatePositions prop → fallback
  // to auto-placed positions derived from names only.
  const initCandidates = useCallback((): CandidatePos[] => {
    if (initialCandidatePositions && initialCandidatePositions.length > 0) {
      return initialCandidatePositions.slice(0, 6).map((c) => ({
        name: c.name,
        x:    Math.max(-1, Math.min(1, c.x)),
        y:    Math.max(-1, Math.min(1, c.y)),
      }));
    }
    const names = defaultCandidates?.filter(Boolean).slice(0, 6) ?? ['Alice', 'Bob', 'Charlie'];
    return names.map((name, i) => ({
      name,
      x: Math.round((-0.6 + (i * 0.6)) * 10) / 10,
      y: Math.round((-0.3 + (i * 0.15)) * 10) / 10,
    }));
  }, [defaultCandidates, initialCandidatePositions]);

  const [candidatePositions, setCandidatePositions] = useState<CandidatePos[]>(initCandidates);

  // Reset when defaultCandidates or initialCandidatePositions prop changes
  useEffect(() => { setCandidatePositions(initCandidates()); }, [initCandidates]);

  // ── Map data
  const [mapData,  setMapData]  = useState<IdeologyMapResult | null>(null);
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState<string | null>(null);

  // ── Drag state
  const [draggingIdx, setDraggingIdx] = useState<number | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  // ── Tooltip state
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);

  // ── Animation broadcast (embedded mode only) — lets the central map react
  //   to the active VoteStepAnimator: greys out eliminated candidates and
  //   draws transfer arrows from the latest eliminated to the beneficiaries.
  const { frame: animFrame } = useAnimationBroadcast();
  const animActive = embedded && animFrame !== null;
  const eliminatedSet = useMemo(
    () => new Set(animActive ? (animFrame?.eliminatedSet ?? []) : []),
    [animActive, animFrame]
  );
  const latestEliminated = useMemo(() => {
    if (!animActive || !animFrame?.eliminated) return [] as string[];
    return animFrame.eliminated.split(' + ').map((s) => s.trim()).filter(Boolean);
  }, [animActive, animFrame]);
  const transferTargets = useMemo(() => {
    if (!animActive || !animFrame?.transfers) return [] as Array<{ name: string; pct: number }>;
    return Object.entries(animFrame.transfers).map(([name, v]) => ({ name, pct: v }));
  }, [animActive, animFrame]);

  // ── Fetch map data
  const fetchMap = useCallback(async (candidates: CandidatePos[]) => {
    if (candidates.length < 2) return;
    setLoading(true);
    setError(null);
    try {
      const params: IdeologyMapParams = {
        num_voters:  numVoters,
        candidates,
        ideology,
        seed,
        method_a: methodA,
        method_b: methodB,
      };
      setMapData(await getIdeologyMap(params));
    } catch {
      setError(t('ideologyMap.error'));
    } finally {
      setLoading(false);
    }
  }, [numVoters, ideology, seed, methodA, methodB, t]);

  // Initial fetch
  useEffect(() => { fetchMap(candidatePositions); }, // eslint-disable-next-line
  [numVoters, ideology, seed, methodA, methodB]);

  // ── Unified mouse + touch drag via useDragTouch ───────────────────────────
  useDragTouch(svgRef, {
    onStart: (_x, _y) => { /* index tracked via handleCandidatePointerDown */ },
    onMove:  (x, y) => {
      if (draggingIdx === null) return;
      setCandidatePositions((prev) =>
        prev.map((c, i) => (i === draggingIdx ? { ...c, x, y } : c))
      );
    },
    onEnd: () => {
      setDraggingIdx(null);
      setTimeout(() => {
        setCandidatePositions((current) => { fetchMap(current); return current; });
      }, 150);
    },
    toDomain: svgToDomain,
  });

  const handleCandidateMouseDown = (e: React.MouseEvent, idx: number) => {
    if (embedded) return;  // dragging disabled — positions come from scenario
    e.preventDefault();
    setDraggingIdx(idx);
    setTooltip(null);
  };

  const handleCandidateTouchStart = (e: React.TouchEvent, idx: number) => {
    if (embedded) return;
    e.stopPropagation();
    setDraggingIdx(idx);
    setTooltip(null);
  };

  const regenerateSeed = () => setSeed(Math.floor(Math.random() * 100_000));

  // ── Voter rendering helpers
  const voterColor = (v: IdeologyMapVoter): string => {
    if (showLosers) {
      const best = Math.max(v.utility_winner_a, v.utility_winner_b);
      return best < 0.3 ? COLOR_LOSE : v.prefers_a ? COLOR_A : COLOR_B;
    }
    return v.prefers_a ? COLOR_A : COLOR_B;
  };

  const voterRadius = (v: IdeologyMapVoter): number => {
    const u = Math.max(v.utility_winner_a, v.utility_winner_b);
    return 2.5 + u * 3;  // 2.5 → 5.5px
  };

  // ── Voronoi regions (updated in real time during drag) ──────────────────
  const voronoiPaths = useMemo(() => {
    if (!showVoronoi || candidatePositions.length < 2) return [];
    return buildVoronoiPaths(candidatePositions, SVG_W, SVG_H, domainToSvg);
  }, [showVoronoi, candidatePositions]);

  const voters     = mapData?.voters     ?? [];
  const candidates = mapData?.candidates ?? candidatePositions.map((c) => ({ ...c, party: 'Independent' }));
  const winnerA    = mapData?.winner_a   ?? null;
  const winnerB    = mapData?.winner_b   ?? null;
  const condorcet  = mapData?.condorcet_winner ?? null;
  const pctA       = mapData ? Math.round(mapData.pct_better_off_with_a * 100) : 50;
  const pctB       = 100 - pctA;
  const different  = winnerA && winnerB && winnerA !== winnerB;

  return (
    <Row className="g-3">
      {/* ── Controls (hidden in embedded mode — parent page already provides config) ── */}
      {!embedded && (
      <Col xs={12} lg={3}>
        <Card>
          <Card.Header className="py-2">
            <strong style={{ fontSize: '0.85rem' }}>{t('ideologyMap.controls')}</strong>
          </Card.Header>
          <Card.Body className="p-2">
            <Form.Label className="small mb-1">{t('ideologyMap.methodA')}</Form.Label>
            <Form.Select
              size="sm" value={methodA} className="mb-2"
              style={{ borderLeft: `3px solid ${COLOR_A}` }}
              onChange={(e) => setMethodA(e.target.value)}
            >
              {METHODS.map((m) => <option key={m} value={m}>{m}</option>)}
            </Form.Select>

            <Form.Label className="small mb-1">{t('ideologyMap.methodB')}</Form.Label>
            <Form.Select
              size="sm" value={methodB} className="mb-2"
              style={{ borderLeft: `3px solid ${COLOR_B}` }}
              onChange={(e) => setMethodB(e.target.value)}
            >
              {METHODS.map((m) => <option key={m} value={m}>{m}</option>)}
            </Form.Select>

            <Form.Label className="small mb-1">
              {t('ideologyMap.numVoters')} : <strong>{numVoters}</strong>
            </Form.Label>
            <Form.Range
              min={50} max={500} step={50} value={numVoters} className="mb-2"
              onChange={(e) => setNumVoters(Number(e.target.value))}
            />

            <Form.Label className="small mb-1">{t('ideologyMap.ideology')}</Form.Label>
            <Form.Select
              size="sm" value={ideology} className="mb-2"
              onChange={(e) => setIdeology(e.target.value)}
            >
              {['random','centrist','polarized','left_skewed','right_skewed'].map((v) => (
                <option key={v} value={v}>{t(`ideology.${v}`)}</option>
              ))}
            </Form.Select>

            <Form.Check
              type="switch"
              id="show-losers-toggle"
              label={<span className="small">{t('ideologyMap.showLosers')}</span>}
              checked={showLosers}
              onChange={(e) => setShowLosers(e.target.checked)}
              className="mb-2"
            />
            <Form.Check
              type="switch"
              id="show-voronoi-toggle"
              label={<span className="small">{t('ideologyMap.showVoronoi')}</span>}
              checked={showVoronoi}
              onChange={(e) => setShowVoronoi(e.target.checked)}
              className="mb-2"
            />
            <Form.Check
              type="switch"
              id="show-median-toggle"
              label={<span className="small">{t('ideologyMap.showMedian')}</span>}
              checked={showMedian}
              onChange={(e) => setShowMedian(e.target.checked)}
              className="mb-3"
              data-testid="show-median-toggle"
            />

            {/* View mode toggle */}
            <div className="mb-3">
              <Form.Label className="small mb-1">{t('heatmap.viewMode')}</Form.Label>
              <ButtonGroup size="sm" className="w-100">
                {(['points', 'heatmap', 'both'] as const).map((mode) => (
                  <Button
                    key={mode}
                    variant={viewMode === mode ? 'secondary' : 'outline-secondary'}
                    onClick={() => setViewMode(mode)}
                    data-testid={`view-mode-${mode}`}
                    style={{ fontSize: '0.75rem' }}
                  >
                    {t(`heatmap.mode_${mode}`)}
                  </Button>
                ))}
              </ButtonGroup>
            </div>

            <Button
              variant="outline-secondary" size="sm" className="w-100"
              onClick={regenerateSeed}
            >
              🎲 {t('ideologyMap.regenerate')}
            </Button>

            {loading && (
              <div className="text-center mt-2">
                <Spinner size="sm" className="me-1" />
                <span className="small text-muted">{t('ideologyMap.loading')}</span>
              </div>
            )}
          </Card.Body>
        </Card>
      </Col>
      )}

      {/* ── Canvas (takes full width in embedded mode) ── */}
      <Col xs={12} lg={embedded ? 12 : 9}>
        {/* ── Compact layer toggles (embedded mode only) ── */}
        {embedded && (
          <div
            className="d-flex gap-1 flex-wrap mb-2 align-items-center"
            style={{ fontSize: '0.7rem' }}
            data-testid="embedded-layer-bar"
          >
            <span className="text-muted me-1">{t('heatmap.viewMode')}:</span>
            <ButtonGroup size="sm">
              {(['points', 'heatmap', 'both'] as const).map((mode) => (
                <Button
                  key={mode}
                  variant={viewMode === mode ? 'secondary' : 'outline-secondary'}
                  onClick={() => setViewMode(mode)}
                  style={{ fontSize: '0.66rem', padding: '2px 8px' }}
                  data-testid={`embedded-view-${mode}`}
                >
                  {t(`heatmap.mode_${mode}`)}
                </Button>
              ))}
            </ButtonGroup>
            <span className="text-muted ms-2 me-1">|</span>
            <Form.Check
              type="switch"
              id="emb-show-voronoi"
              checked={showVoronoi}
              onChange={(e) => setShowVoronoi(e.target.checked)}
              label={<span style={{ fontSize: '0.66rem' }}>{t('ideologyMap.showVoronoi')}</span>}
              className="mb-0 ms-1"
            />
            <Form.Check
              type="switch"
              id="emb-show-median"
              checked={showMedian}
              onChange={(e) => setShowMedian(e.target.checked)}
              label={<span style={{ fontSize: '0.66rem' }}>{t('ideologyMap.showMedian')}</span>}
              className="mb-0 ms-1"
            />
            <Form.Check
              type="switch"
              id="emb-show-losers"
              checked={showLosers}
              onChange={(e) => setShowLosers(e.target.checked)}
              label={<span style={{ fontSize: '0.66rem' }}>{t('ideologyMap.showLosers')}</span>}
              className="mb-0 ms-1"
            />
            {animActive && (
              <Badge
                bg="success"
                className="ms-2"
                style={{ fontSize: '0.65rem' }}
                data-testid="anim-live-badge"
              >
                ● {t('lab.animLiveOnMap', { method: animFrame?.method ?? '', step: animFrame?.step ?? 1, total: animFrame?.totalSteps ?? 1 })}
              </Badge>
            )}
          </div>
        )}
        <Card>
          <Card.Body className="p-2">
            {error && <div className="text-danger small mb-2">{error}</div>}

            {/* ── Heatmap view ── */}
            {(viewMode === 'heatmap' || viewMode === 'both') && (
              <div className={viewMode === 'both' ? 'mb-3' : ''} data-testid="heatmap-container">
                <IdeologyHeatmap
                  voters={voters.map((v) => ({ id: v.id, x: v.x, y: v.y }))}
                  candidates={candidatePositions}
                  onCandidateMouseDown={handleCandidateMouseDown}
                  draggingIdx={draggingIdx}
                />
              </div>
            )}

            {/* ── Scatter (points) view ── */}
            {(viewMode === 'points' || viewMode === 'both') && <svg
              ref={svgRef}
              viewBox={`0 0 ${SVG_W} ${SVG_H}`}
              width="100%"
              style={{
                maxHeight: 520,
                cursor: draggingIdx !== null ? 'grabbing' : 'crosshair',
                userSelect: 'none',
                display: 'block',
              }}
            >
              {/* Grid */}
              {[-0.5, 0, 0.5].map((v) => (
                <React.Fragment key={v}>
                  <line
                    x1={domainToSvg(v, 'x')} y1={MARGIN}
                    x2={domainToSvg(v, 'x')} y2={SVG_H - MARGIN}
                    stroke={v === 0 ? '#adb5bd' : '#dee2e6'} strokeWidth={v === 0 ? 1.5 : 0.8}
                    strokeDasharray={v === 0 ? undefined : '3 3'}
                  />
                  <line
                    x1={MARGIN} y1={domainToSvg(v, 'y')}
                    x2={SVG_W - MARGIN} y2={domainToSvg(v, 'y')}
                    stroke={v === 0 ? '#adb5bd' : '#dee2e6'} strokeWidth={v === 0 ? 1.5 : 0.8}
                    strokeDasharray={v === 0 ? undefined : '3 3'}
                  />
                </React.Fragment>
              ))}

              {/* Axis labels */}
              <text x={MARGIN} y={SVG_H - 8} fontSize={10} fill="#6c757d">{t('ideologyMap.axisLeft')}</text>
              <text x={SVG_W - MARGIN} y={SVG_H - 8} textAnchor="end" fontSize={10} fill="#6c757d">{t('ideologyMap.axisRight')}</text>
              <text x={8} y={MARGIN + 4} fontSize={10} fill="#6c757d" transform={`rotate(-90 8 ${MARGIN + 4})`}>{t('ideologyMap.axisLiberal')}</text>
              <text x={8} y={SVG_H - MARGIN} fontSize={10} fill="#6c757d" transform={`rotate(-90 8 ${SVG_H - MARGIN})`}>{t('ideologyMap.axisConservative')}</text>

              {/* Voronoi regions — rendered UNDER voter dots */}
              {voronoiPaths.map((region, idx) =>
                region.path ? (
                  <path
                    key={region.name}
                    d={region.path}
                    fill={VORONOI_COLORS[idx % VORONOI_COLORS.length]}
                    fillOpacity={0.12}
                    stroke={VORONOI_COLORS[idx % VORONOI_COLORS.length]}
                    strokeWidth={1.5}
                    strokeOpacity={0.4}
                    style={{ transition: 'fill 0.3s, stroke 0.3s', pointerEvents: 'none' }}
                    data-testid={`voronoi-region-${region.name}`}
                  />
                ) : null
              )}

              {/* Voter dots */}
              {voters.map((v) => (
                <circle
                  key={v.id}
                  cx={domainToSvg(v.x, 'x')}
                  cy={domainToSvg(v.y, 'y')}
                  r={voterRadius(v)}
                  fill={voterColor(v)}
                  fillOpacity={showLosers && Math.max(v.utility_winner_a, v.utility_winner_b) < 0.3 ? 0.8 : 0.35}
                  style={{ cursor: 'default' }}
                  onMouseEnter={(e) => setTooltip({
                    voter: v,
                    screenX: e.clientX,
                    screenY: e.clientY,
                    winnerA, winnerB,
                  })}
                  onMouseLeave={() => setTooltip(null)}
                />
              ))}

              {/* Median voter layer — after dots, before candidate stars */}
              {showMedian && voters.length > 0 && (
                <MedianVoterLayer
                  voters={voters.map(v => ({ x: v.x, y: v.y }))}
                  candidates={candidatePositions}
                  winnerA={winnerA}
                  winnerB={winnerB}
                  methodA={methodA}
                  methodB={methodB}
                />
              )}

              {/* Transfer arrows (animation overlay, embedded mode only) —
                  drawn from the latest-eliminated candidate(s) toward the
                  beneficiaries, sized by transfer share. */}
              {animActive && latestEliminated.length > 0 && transferTargets.length > 0 && (
                <g data-testid="anim-transfer-arrows">
                  <defs>
                    <marker
                      id="anim-arrow-head"
                      viewBox="0 0 10 10" refX="8" refY="5"
                      markerWidth="6" markerHeight="6" orient="auto-start-reverse"
                    >
                      <path d="M 0 0 L 10 5 L 0 10 z" fill="#007A33" />
                    </marker>
                  </defs>
                  {latestEliminated.flatMap((elimName) => {
                    const src = candidatePositions.find((c) => c.name === elimName);
                    if (!src) return [];
                    const x1 = domainToSvg(src.x, 'x');
                    const y1 = domainToSvg(src.y, 'y');
                    return transferTargets
                      .filter((tt) => tt.name !== elimName && tt.pct > 0)
                      .map((tt) => {
                        const dst = candidatePositions.find((c) => c.name === tt.name);
                        if (!dst) return null;
                        const x2 = domainToSvg(dst.x, 'x');
                        const y2 = domainToSvg(dst.y, 'y');
                        const sw = 1 + Math.min(4, tt.pct * 8);
                        return (
                          <line
                            key={`${elimName}->${tt.name}`}
                            x1={x1} y1={y1} x2={x2} y2={y2}
                            stroke="#007A33" strokeWidth={sw}
                            strokeOpacity={0.55}
                            markerEnd="url(#anim-arrow-head)"
                            style={{ pointerEvents: 'none' }}
                          />
                        );
                      })
                      .filter(Boolean);
                  })}
                </g>
              )}

              {/* Candidates (draggable stars) */}
              {candidatePositions.map((cp, idx) => {
                const cx = domainToSvg(cp.x, 'x');
                const cy = domainToSvg(cp.y, 'y');
                const color = PARTY_COLORS[candidates[idx]?.party ?? 'Independent'] ?? '#6c757d';
                const isWinnerA = winnerA === cp.name;
                const isWinnerB = winnerB === cp.name;
                const isEliminated = eliminatedSet.has(cp.name);
                const isJustEliminated = latestEliminated.includes(cp.name);
                const starOpacity = isEliminated ? 0.3 : 1;
                return (
                  <g
                    key={cp.name}
                    transform={`translate(${cx},${cy})`}
                    style={{
                      cursor: draggingIdx === idx ? 'grabbing' : 'grab',
                      touchAction: 'none',
                      transition: 'opacity 0.3s',
                    }}
                    opacity={starOpacity}
                    onMouseDown={(e) => handleCandidateMouseDown(e, idx)}
                    onTouchStart={(e) => handleCandidateTouchStart(e, idx)}
                  >
                    {/* Highlight ring for winners */}
                    {(isWinnerA || isWinnerB) && !isEliminated && (
                      <circle r={20} fill="none" strokeWidth={2.5}
                        stroke={isWinnerA && isWinnerB ? '#7B2D8B' : isWinnerA ? COLOR_A : COLOR_B}
                        strokeDasharray={isWinnerA && isWinnerB ? '4 2' : undefined}
                      />
                    )}
                    {/* Red pulse ring for the latest eliminated candidate(s) */}
                    {isJustEliminated && (
                      <circle r={18} fill="none" strokeWidth={2.5}
                        stroke={COLOR_LOSE} strokeDasharray="3 3"
                        data-testid={`elim-ring-${cp.name}`}
                      />
                    )}
                    {/* Star symbol */}
                    <text
                      textAnchor="middle" dominantBaseline="central"
                      fontSize={22}
                      fill={isEliminated ? '#999' : color}
                      stroke="#fff" strokeWidth={0.8}
                      style={{ pointerEvents: 'none', userSelect: 'none' }}
                      textDecoration={isEliminated ? 'line-through' : undefined}
                    >★</text>
                    {/* Label */}
                    <text
                      y={-20} textAnchor="middle" fontSize={11}
                      fill={isEliminated ? '#999' : color} fontWeight={600}
                      stroke="#fff" strokeWidth={3} paintOrder="stroke"
                      style={{ pointerEvents: 'none' }}
                    >{cp.name}</text>
                  </g>
                );
              })}
            </svg>}

            {/* Median voter legend (when active) */}
            {showMedian && voters.length > 0 && (
              <MedianVoterLegend
                voters={voters.map(v => ({ x: v.x, y: v.y }))}
                candidates={candidatePositions}
                winnerA={winnerA}
                winnerB={winnerB}
                methodA={methodA}
                methodB={methodB}
              />
            )}

            {/* Legend */}
            <div className="d-flex gap-3 mt-1 flex-wrap" style={{ fontSize: '0.75rem' }}>
              <span className="d-flex align-items-center gap-1">
                <span style={{ width: 10, height: 10, borderRadius: '50%', background: COLOR_A, display: 'inline-block' }} />
                {t('ideologyMap.prefersA')} {winnerA ? `(${winnerA})` : ''}
              </span>
              <span className="d-flex align-items-center gap-1">
                <span style={{ width: 10, height: 10, borderRadius: '50%', background: COLOR_B, display: 'inline-block' }} />
                {t('ideologyMap.prefersB')} {winnerB ? `(${winnerB})` : ''}
              </span>
              {showLosers && (
                <span className="d-flex align-items-center gap-1">
                  <span style={{ width: 10, height: 10, borderRadius: '50%', background: COLOR_LOSE, display: 'inline-block' }} />
                  {t('ideologyMap.lowUtility')}
                </span>
              )}
            </div>

            {/* Voronoi legend */}
            {showVoronoi && candidatePositions.length > 0 && (
              <div className="d-flex align-items-center gap-2 flex-wrap mt-2" style={{ fontSize: '0.75rem' }}>
                <span className="text-muted fw-semibold">{t('ideologyMap.voronoiLegend')}:</span>
                {candidatePositions.map((cp, idx) => (
                  <Badge
                    key={cp.name}
                    style={{
                      background:  VORONOI_COLORS[idx % VORONOI_COLORS.length],
                      fontSize:    '0.68rem',
                      opacity:     voronoiPaths.find((r) => r.name === cp.name)?.path ? 1 : 0.4,
                    }}
                  >
                    {cp.name}
                  </Badge>
                ))}
              </div>
            )}

            {/* ── Stats panel ── */}
            {mapData && (
              <div className="mt-3">
                {/* Progress bar */}
                <div className="mb-1" style={{ fontSize: '0.78rem', color: '#6c757d' }}>
                  {pctA}% {t('ideologyMap.prefer')} <strong style={{ color: COLOR_A }}>{methodA}</strong>
                  {' / '}
                  {pctB}% {t('ideologyMap.prefer')} <strong style={{ color: COLOR_B }}>{methodB}</strong>
                </div>
                <div className="d-flex rounded overflow-hidden mb-3" style={{ height: 14 }}>
                  <div style={{ width: `${pctA}%`, background: COLOR_A, transition: 'width 0.4s' }} />
                  <div style={{ width: `${pctB}%`, background: COLOR_B, transition: 'width 0.4s' }} />
                </div>

                {/* Winner badges */}
                <div className="d-flex gap-2 flex-wrap mb-2">
                  <span className="small text-muted">{t('ideologyMap.winners')}</span>
                  {winnerA && (
                    <Badge style={{ background: COLOR_A }}>
                      {methodA}: {winnerA}
                      {condorcet === winnerA && ' ✓'}
                    </Badge>
                  )}
                  {winnerB && winnerB !== winnerA && (
                    <Badge style={{ background: COLOR_B }}>
                      {methodB}: {winnerB}
                      {condorcet === winnerB && ' ✓'}
                    </Badge>
                  )}
                  {condorcet && (
                    <Badge bg="secondary">Condorcet: {condorcet}</Badge>
                  )}
                </div>

                {/* Divergence message */}
                {different && (
                  <div
                    className="rounded p-2"
                    style={{ background: '#fff8e1', border: '1px solid #f9a825', fontSize: '0.8rem' }}
                  >
                    ⚠️ {t('ideologyMap.divergence', { a: methodA, b: methodB })}
                  </div>
                )}
              </div>
            )}
          </Card.Body>
        </Card>
      </Col>

      {/* Floating tooltip */}
      {tooltip && <VoterTooltip tip={tooltip} t={t} />}
    </Row>
  );
};

export default IdeologyMapChart;
