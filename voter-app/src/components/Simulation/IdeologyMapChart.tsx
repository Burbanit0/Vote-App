import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Badge, Button, ButtonGroup, Card, Col, Form, ProgressBar, Row, Spinner,
} from 'react-bootstrap';
import IdeologyHeatmap from './IdeologyHeatmap';
import MedianVoterLayer, { MedianVoterLegend } from './MedianVoterLayer';
import { useTranslation } from 'react-i18next';
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
}

const IdeologyMapChart: React.FC<Props> = ({ defaultCandidates }) => {
  const { t } = useTranslation();

  // ── Controls state
  const [methodA,      setMethodA]      = useState('plurality');
  const [methodB,      setMethodB]      = useState('schulze');
  const [numVoters,    setNumVoters]    = useState(200);
  const [ideology,     setIdeology]     = useState('random');
  const [seed,         setSeed]         = useState(42);
  const [showLosers,   setShowLosers]   = useState(false);
  const [showVoronoi,  setShowVoronoi]  = useState(false);
  const [viewMode,     setViewMode]     = useState<'points' | 'heatmap' | 'both'>('points');
  const [showMedian,   setShowMedian]   = useState(false);

  // ── Candidate positions (draggable)
  const initCandidates = useCallback((): CandidatePos[] => {
    const names = defaultCandidates?.filter(Boolean).slice(0, 6) ?? ['Alice', 'Bob', 'Charlie'];
    return names.map((name, i) => ({
      name,
      x: Math.round((-0.6 + (i * 0.6)) * 10) / 10,
      y: Math.round((-0.3 + (i * 0.15)) * 10) / 10,
    }));
  }, [defaultCandidates]);

  const [candidatePositions, setCandidatePositions] = useState<CandidatePos[]>(initCandidates);

  // Reset when defaultCandidates prop changes
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

  // ── Drag handlers (window-level to capture fast movement)
  useEffect(() => {
    if (draggingIdx === null) return;

    const onMove = (e: MouseEvent) => {
      if (!svgRef.current) return;
      const { x, y } = svgToDomain(e.clientX, e.clientY, svgRef.current.getBoundingClientRect());
      setCandidatePositions((prev) =>
        prev.map((c, i) => (i === draggingIdx ? { ...c, x, y } : c))
      );
    };

    const onUp = () => {
      setDraggingIdx(null);
      // Trigger API call 150ms after drop
      setTimeout(() => {
        setCandidatePositions((current) => { fetchMap(current); return current; });
      }, 150);
    };

    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup',  onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup',  onUp);
    };
  }, [draggingIdx, fetchMap]);

  const handleCandidateMouseDown = (e: React.MouseEvent, idx: number) => {
    e.preventDefault();
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
      {/* ── Controls ── */}
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

      {/* ── Canvas ── */}
      <Col xs={12} lg={9}>
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

              {/* Candidates (draggable stars) */}
              {candidatePositions.map((cp, idx) => {
                const cx = domainToSvg(cp.x, 'x');
                const cy = domainToSvg(cp.y, 'y');
                const color = PARTY_COLORS[candidates[idx]?.party ?? 'Independent'] ?? '#6c757d';
                const isWinnerA = winnerA === cp.name;
                const isWinnerB = winnerB === cp.name;
                return (
                  <g
                    key={cp.name}
                    transform={`translate(${cx},${cy})`}
                    style={{ cursor: draggingIdx === idx ? 'grabbing' : 'grab' }}
                    onMouseDown={(e) => handleCandidateMouseDown(e, idx)}
                  >
                    {/* Highlight ring for winners */}
                    {(isWinnerA || isWinnerB) && (
                      <circle r={20} fill="none" strokeWidth={2.5}
                        stroke={isWinnerA && isWinnerB ? '#7B2D8B' : isWinnerA ? COLOR_A : COLOR_B}
                        strokeDasharray={isWinnerA && isWinnerB ? '4 2' : undefined}
                      />
                    )}
                    {/* Star symbol */}
                    <text
                      textAnchor="middle" dominantBaseline="central"
                      fontSize={22} fill={color} stroke="#fff" strokeWidth={0.8}
                      style={{ pointerEvents: 'none', userSelect: 'none' }}
                    >★</text>
                    {/* Label */}
                    <text
                      y={-20} textAnchor="middle" fontSize={11}
                      fill={color} fontWeight={600}
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
