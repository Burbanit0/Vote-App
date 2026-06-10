import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useDragTouch } from '../../hooks/useDragTouch';
import { useTranslation } from 'react-i18next';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardBody } from '@/components/ui/card';
import { Range } from '@/components/ui/form-controls';
import { Col, Row } from '@/components/ui/grid';
import { Spinner } from '@/components/ui/spinner';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { $api } from '../../api/hooks';
import type { HistoricalReplayResponse } from '../../api';

// ── Types ─────────────────────────────────────────────────────────────────────
// Source of truth is the generated `HistoricalReplayResponse` (Phase 6 response_model).

type ReplayData = HistoricalReplayResponse;
type ReplayCandidate = HistoricalReplayResponse['candidates'][number];
type DaySnapshot = HistoricalReplayResponse['days'][number];

// ── Scenario cards config ─────────────────────────────────────────────────────

const SCENARIOS = [
  { id: 'france2002', flag: '🇫🇷', name: 'France 2002', phenomenon: 'Paradoxe de Condorcet' },
  { id: 'usa1992', flag: '🇺🇸', name: 'USA 1992', phenomenon: 'Effet spoiler' },
  { id: 'germany2021', flag: '🇩🇪', name: 'Allemagne 2021', phenomenon: 'Fragmentation' },
  { id: 'condorcet_cycle', flag: '📐', name: 'Cycle de Condorcet', phenomenon: 'Intransitivité' },
] as const;

// ── Palette ───────────────────────────────────────────────────────────────────

const PALETTE = ['#005CAB', '#C8590A', '#007A33', '#6c757d', '#9b59b6', '#e67e22'];

function candColor(name: string, names: string[]): string {
  return PALETTE[names.indexOf(name) % PALETTE.length] ?? '#888';
}

// ── SVG ideology map ──────────────────────────────────────────────────────────

const SVG_W = 360;
const SVG_H = 300;
const PAD = 28;

function domX(v: number) {
  return PAD + ((v + 1) / 2) * (SVG_W - 2 * PAD);
}
function domY(v: number) {
  return PAD + ((1 - v) / 2) * (SVG_H - 2 * PAD);
}
function svgToDomain(px: number, py: number, rect: DOMRect) {
  const x = ((((px - rect.left) / rect.width) * SVG_W - PAD) / (SVG_W - 2 * PAD)) * 2 - 1;
  const y = 1 - ((((py - rect.top) / rect.height) * SVG_H - PAD) / (SVG_H - 2 * PAD)) * 2;
  return { x: Math.max(-1, Math.min(1, x)), y: Math.max(-1, Math.min(1, y)) };
}

interface IdeologyMapProps {
  candidates: ReplayCandidate[];
  onMove: (name: string, x: number, y: number) => void;
  candidateNames: string[];
}

const IdeologyMap: React.FC<IdeologyMapProps> = ({ candidates, onMove, candidateNames }) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const draggingRef = useRef<string | null>(null);

  useDragTouch(svgRef, {
    onStart: () => {},
    onMove: (x, y) => {
      if (draggingRef.current) onMove(draggingRef.current, x, y);
    },
    onEnd: () => {
      draggingRef.current = null;
    },
    toDomain: svgToDomain,
  });

  return (
    <svg
      ref={svgRef}
      data-testid="ideology-map-svg"
      viewBox={`0 0 ${SVG_W} ${SVG_H}`}
      width="100%"
      style={{ maxHeight: 280, display: 'block', cursor: 'crosshair', userSelect: 'none' }}
    >
      {/* Grid */}
      <line
        x1={SVG_W / 2}
        y1={PAD}
        x2={SVG_W / 2}
        y2={SVG_H - PAD}
        stroke="#dee2e6"
        strokeWidth={1}
      />
      <line
        x1={PAD}
        y1={SVG_H / 2}
        x2={SVG_W - PAD}
        y2={SVG_H / 2}
        stroke="#dee2e6"
        strokeWidth={1}
      />
      <rect
        x={PAD}
        y={PAD}
        width={SVG_W - 2 * PAD}
        height={SVG_H - 2 * PAD}
        fill="none"
        stroke="#ced4da"
        strokeWidth={0.8}
      />
      <text x={PAD} y={SVG_H - 8} fontSize={9} fill="#adb5bd">
        ← Gauche
      </text>
      <text x={SVG_W - PAD} y={SVG_H - 8} textAnchor="end" fontSize={9} fill="#adb5bd">
        Droite →
      </text>

      {/* Candidates */}
      {candidates.map((c) => {
        const cx = domX(c.x);
        const cy = domY(c.y);
        const color = candColor(c.name, candidateNames);
        return (
          <g
            key={c.name}
            transform={`translate(${cx},${cy})`}
            style={{ cursor: 'grab', touchAction: 'none' }}
            onMouseDown={(e) => {
              e.preventDefault();
              draggingRef.current = c.name;
            }}
            onTouchStart={(e) => {
              e.stopPropagation();
              draggingRef.current = c.name;
            }}
            data-testid={`candidate-star-${c.name}`}
          >
            {c.modified && (
              <circle r={16} fill="none" stroke={color} strokeWidth={2} strokeDasharray="3 2" />
            )}
            <text
              textAnchor="middle"
              dominantBaseline="central"
              fontSize={20}
              fill={color}
              stroke="#fff"
              strokeWidth={0.7}
              style={{ pointerEvents: 'none' }}
            >
              ★
            </text>
            <text
              y={-18}
              textAnchor="middle"
              fontSize={10}
              fontWeight={600}
              fill={color}
              stroke="#fff"
              strokeWidth={2.5}
              paintOrder="stroke"
              style={{ pointerEvents: 'none' }}
            >
              {c.name.split(' ')[0]}
              {c.modified ? ' ↺' : ''}
            </text>
          </g>
        );
      })}
    </svg>
  );
};

// ── Main component ────────────────────────────────────────────────────────────

const HistoricalReplay: React.FC = () => {
  const { t, i18n } = useTranslation();
  const lang = i18n.language?.startsWith('en') ? 'en' : 'fr';

  const [scenarioId, setScenarioId] = useState<string>('france2002');
  const [numDays, setNumDays] = useState(30);
  const sim = $api.useMutation('post', '/api/v2/election/historical-replay');
  const data: ReplayData | null = sim.data ?? null;
  const loading = sim.isPending;
  const error = sim.isError ? t('replay.error') : null;
  const [currentDay, setCurrentDay] = useState(0);
  const [playing, setPlaying] = useState(false);

  // Candidate positions (controlled for drag)
  const [positions, setPositions] = useState<Record<string, { x: number; y: number }>>({});

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Derive overrides from positions that differ from scenario defaults
  const scenarioCandidates = SCENARIOS.find((s) => s.id === scenarioId) ? [] : [];

  const candidateNames = data?.candidates.map((c) => c.name) ?? [];

  function run(overrides: { name: string; x: number; y: number }[] = []) {
    if (timerRef.current) clearTimeout(timerRef.current);
    setPlaying(false);
    setCurrentDay(0);
    sim.mutate(
      {
        body: {
          scenario_id: scenarioId,
          overrides,
          num_days: numDays,
          seed: 42,
        },
      },
      {
        onSuccess: (res) => {
          // Init positions from returned candidates
          const p: Record<string, { x: number; y: number }> = {};
          res.candidates.forEach((c) => {
            p[c.name] = { x: c.x, y: c.y };
          });
          setPositions(p);
        },
      }
    );
  }

  // Play/pause auto-advance
  useEffect(() => {
    if (!playing || !data) return;
    if (currentDay >= data.days.length - 1) {
      setPlaying(false);
      return;
    }
    timerRef.current = setTimeout(() => setCurrentDay((d) => d + 1), 500);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [playing, currentDay, data]);

  useEffect(
    () => () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    },
    []
  );

  const handleCandidateMove = useCallback((name: string, x: number, y: number) => {
    setPositions((prev) => ({ ...prev, [name]: { x, y } }));
  }, []);

  const applyDragAndReplay = useCallback(() => {
    if (!data) return;
    const overrides = data.candidates
      .filter((c) => {
        const p = positions[c.name];
        return p && (Math.abs(p.x - c.x) > 0.02 || Math.abs(p.y - c.y) > 0.02);
      })
      .map((c) => ({ name: c.name, ...positions[c.name] }));
    run(overrides);
  }, [data, positions, scenarioId, numDays]);

  const snapshot = data?.days[currentDay];
  const differs = data?.final.differs_from_real;

  const chartData = snapshot
    ? Object.entries(snapshot.vote_shares)
        .sort(([, a], [, b]) => b - a)
        .map(([name, pct]) => ({ name, pct: Math.round(pct * 100) }))
    : [];

  // Candidates with drag-updated positions
  const displayCandidates: ReplayCandidate[] =
    data?.candidates.map((c) => ({
      ...c,
      x: positions[c.name]?.x ?? c.x,
      y: positions[c.name]?.y ?? c.y,
    })) ?? [];

  return (
    <div>
      {/* ── Scenario selector ── */}
      <Row className="g-2 mb-3">
        {SCENARIOS.map((sc) => (
          <Col xs={6} sm={3} key={sc.id}>
            <Card
              className="h-full"
              style={{
                cursor: 'pointer',
                border: scenarioId === sc.id ? '2px solid var(--bs-primary)' : undefined,
                fontSize: '0.78rem',
              }}
              onClick={() => {
                setScenarioId(sc.id);
                sim.reset();
                setPositions({});
              }}
              data-testid={`scenario-card-${sc.id}`}
            >
              <CardBody className="p-2 text-center">
                <div style={{ fontSize: '1.6rem' }}>{sc.flag}</div>
                <div className="font-semibold">{sc.name}</div>
                <Badge variant="secondary" style={{ fontSize: '0.65rem' }}>
                  {sc.phenomenon}
                </Badge>
              </CardBody>
            </Card>
          </Col>
        ))}
      </Row>

      {/* ── Controls ── */}
      <div className="flex gap-2 items-center flex-wrap mb-3">
        <div style={{ flex: '1 1 160px' }}>
          <label className="mb-1 inline-block text-sm mb-0">
            {t('replay.numDays')}: <strong>{numDays}</strong>
          </label>
          <Range
            min={10}
            max={60}
            step={5}
            value={numDays}
            onChange={(e) => setNumDays(Number(e.target.value))}
          />
        </div>
        <Button variant="primary" onClick={() => run()} disabled={loading}>
          {loading ? (
            <>
              <Spinner size="sm" className="me-1" />
              {t('replay.simulating')}
            </>
          ) : (
            `▶ ${t('replay.run')}`
          )}
        </Button>
        {data && (
          <Button
            variant="outline-secondary"
            size="sm"
            onClick={applyDragAndReplay}
            disabled={loading}
            data-testid="apply-drag-btn"
          >
            ↺ {t('replay.applyDrag')}
          </Button>
        )}
      </div>

      {error && <Alert variant="danger">{error}</Alert>}

      {data && (
        <Row className="g-3">
          {/* ── Left: ideology map + day slider ── */}
          <Col xs={12} lg={5}>
            <div className="border border-border rounded p-2 mb-2">
              <div className="text-sm text-muted-foreground mb-1">{t('replay.dragHint')}</div>
              <IdeologyMap
                candidates={displayCandidates}
                onMove={handleCandidateMove}
                candidateNames={candidateNames}
              />
            </div>

            {/* Day slider */}
            <div className="border border-border rounded p-2">
              <div className="flex items-center gap-2 mb-1">
                <Button
                  size="sm"
                  variant={playing ? 'warning' : 'success'}
                  onClick={() => setPlaying(!playing)}
                  style={{ minWidth: 70 }}
                  data-testid="play-button"
                >
                  {playing ? '⏸ Pause' : '▶ Jouer'}
                </Button>
                <Badge variant="secondary" data-testid="day-badge">
                  {t('replay.day')} {currentDay} / {numDays}
                </Badge>
                {snapshot && (
                  <Badge
                    style={{ background: candColor(snapshot.winner_fptp, candidateNames) }}
                    data-testid="current-winner-badge"
                  >
                    FPTP: {snapshot.winner_fptp}
                  </Badge>
                )}
              </div>
              <Range
                min={0}
                max={data.days.length - 1}
                step={1}
                value={currentDay}
                onChange={(e) => {
                  setPlaying(false);
                  setCurrentDay(Number(e.target.value));
                }}
                data-testid="day-slider"
              />
            </div>
          </Col>

          {/* ── Right: bar chart + comparison ── */}
          <Col xs={12} lg={7}>
            {/* Vote share bar chart */}
            <div className="border border-border rounded p-2 mb-2" data-testid="vote-share-chart">
              <div className="text-sm font-semibold mb-1">
                {t('replay.voteShares')} — {t('replay.day')} {currentDay}
              </div>
              <div style={{ height: 150 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={chartData}
                    layout="vertical"
                    margin={{ top: 4, right: 40, bottom: 4, left: 80 }}
                  >
                    <XAxis type="number" domain={[0, 100]} unit="%" tick={{ fontSize: 9 }} />
                    <YAxis type="category" dataKey="name" tick={{ fontSize: 10 }} width={75} />
                    <Tooltip formatter={(v: number) => `${v}%`} />
                    <Bar dataKey="pct" radius={[0, 3, 3, 0]} isAnimationActive={false}>
                      {chartData.map((entry, i) => (
                        <Cell key={i} fill={candColor(entry.name, candidateNames)} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Comparison: real vs simulated */}
            <div
              className="border border-border rounded p-2"
              style={{ fontSize: '0.82rem' }}
              data-testid="comparison-panel"
            >
              <Row className="g-2">
                <Col xs={6}>
                  <div className="font-semibold mb-1">🏛 {t('replay.realResult')}</div>
                  <Badge variant="secondary" style={{ fontSize: '0.8rem' }}>
                    {data.scenario.real_winner}
                  </Badge>
                </Col>
                <Col xs={6}>
                  <div className="font-semibold mb-1">🔬 {t('replay.simResult')}</div>
                  <Badge
                    variant={differs ? 'danger' : 'success'}
                    data-testid="result-badge"
                    style={{ fontSize: '0.8rem' }}
                  >
                    {data.final.winner_fptp}
                    {differs ? ' ✗' : ' ✓'}
                  </Badge>
                </Col>
              </Row>

              <div className="mt-2 flex gap-2 flex-wrap">
                {data.final.winner_condorcet && (
                  <Badge variant="info" style={{ fontSize: '0.72rem' }}>
                    Condorcet: {data.final.winner_condorcet}
                  </Badge>
                )}
                <Badge variant="secondary" style={{ fontSize: '0.72rem' }}>
                  Borda: {data.final.winner_borda}
                </Badge>
                {differs && (
                  <Badge
                    variant="warning"
                    data-testid="divergence-badge"
                    style={{ fontSize: '0.72rem' }}
                  >
                    ⚠ {t('replay.differs')}
                  </Badge>
                )}
              </div>

              {/* Pedagogical note */}
              <Alert
                variant={differs ? 'warning' : 'success'}
                className="mt-2 py-2 mb-0"
                style={{ fontSize: '0.8rem' }}
                data-testid="pedagogical-note"
              >
                {lang === 'en' ? data.final.pedagogical_note_en : data.final.pedagogical_note}
              </Alert>
            </div>
          </Col>
        </Row>
      )}
    </div>
  );
};

export default HistoricalReplay;
