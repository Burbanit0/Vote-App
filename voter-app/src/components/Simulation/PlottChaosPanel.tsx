/**
 * PlottChaosPanel — Interactive demonstration of Plott's Chaos Theorem (1967).
 * In 2D policy space with ≥3 voters, a Condorcet winner almost never exists;
 * an agenda-setter can drive the electorate to ANY policy via pairwise votes.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Control, Range } from '@/components/ui/form-controls';
import { Col, Row } from '@/components/ui/grid';
import { Spinner } from '@/components/ui/spinner';
import { $api } from '../../api/hooks';
const SVG_SIZE = 380;
const PAD = 30;
const ANIM_MS = 700;

// ── Types ─────────────────────────────────────────────────────────────────────

interface PlottData {
  condorcet_winner_exists: boolean;
  top_cycle: { size: number; center: number[] };
  chaos_path: {
    from: number[];
    to: number[];
    steps: number[][];
    num_steps: number;
  };
  alternative_path: { to: number[]; steps: number[][] };
  voter_ideal_points: number[][];
  pedagogical_note: string;
}

// ── Coordinate helpers ────────────────────────────────────────────────────────

function toSVG(v: number): number {
  return PAD + ((v + 1) / 2) * (SVG_SIZE - 2 * PAD);
}

function coord(pt: number[]): [number, number] {
  return [toSVG(pt[0]), toSVG(pt[1] ?? 0)];
}

// ── SVG component ─────────────────────────────────────────────────────────────

interface ChaosMapProps {
  data: PlottData;
  animStep: number; // which step in chaos_path we're showing (-1 = all)
  showAlt: boolean; // show alternative path
}

const ChaosMap: React.FC<ChaosMapProps> = ({ data, animStep, showAlt }) => {
  const steps = data.chaos_path.steps;
  const altSteps = data.alternative_path.steps;
  const visSteps = animStep < 0 ? steps : steps.slice(0, animStep + 1);
  const visAlt = showAlt ? altSteps : [];

  // Top cycle shading: approximate with a circle around center
  const [tcx, tcy] = coord(data.top_cycle.center);
  const tcRadius = Math.min(
    60,
    Math.max(10, (data.top_cycle.size / 100) * (SVG_SIZE - 2 * PAD) * 0.8)
  );

  return (
    <svg
      data-testid="chaos-map-svg"
      width={SVG_SIZE}
      height={SVG_SIZE}
      style={{ border: '1px solid #dee2e6', borderRadius: 8, background: '#f8f9fa' }}
    >
      {/* Axes */}
      <line x1={PAD} y1={SVG_SIZE / 2} x2={SVG_SIZE - PAD} y2={SVG_SIZE / 2} stroke="#dee2e6" />
      <line x1={SVG_SIZE / 2} y1={PAD} x2={SVG_SIZE / 2} y2={SVG_SIZE - PAD} stroke="#dee2e6" />

      {/* Top cycle zone */}
      {!data.condorcet_winner_exists && (
        <circle
          cx={tcx}
          cy={tcy}
          r={tcRadius}
          fill="#dc3545"
          fillOpacity={0.08}
          stroke="#dc3545"
          strokeWidth={1}
          strokeDasharray="6 3"
        />
      )}

      {/* Voter ideal points */}
      {data.voter_ideal_points.map((pt, i) => (
        <circle key={i} cx={coord(pt)[0]} cy={coord(pt)[1]} r={6} fill="#005CAB" opacity={0.7} />
      ))}

      {/* Alternative path */}
      {visAlt.length > 1 && (
        <>
          <polyline
            points={visAlt.map((p) => coord(p).join(',')).join(' ')}
            fill="none"
            stroke="#fd7e14"
            strokeWidth={2}
            strokeDasharray="6 3"
            opacity={0.7}
          />
          {visAlt.map((p, i) => (
            <circle
              key={`alt-${i}`}
              cx={coord(p)[0]}
              cy={coord(p)[1]}
              r={i === 0 ? 8 : 5}
              fill={i === visAlt.length - 1 ? '#fd7e14' : '#ffc107'}
              opacity={0.8}
            />
          ))}
          <text
            x={coord(visAlt[visAlt.length - 1])[0] + 6}
            y={coord(visAlt[visAlt.length - 1])[1]}
            style={{ fontSize: 10, fill: '#fd7e14', fontWeight: 700 }}
          >
            Cible B
          </text>
        </>
      )}

      {/* Main path */}
      {visSteps.length > 1 && (
        <polyline
          points={visSteps.map((p) => coord(p).join(',')).join(' ')}
          fill="none"
          stroke="#198754"
          strokeWidth={2}
          opacity={0.85}
        />
      )}
      {visSteps.map((p, i) => {
        const [cx, cy] = coord(p);
        const isStart = i === 0;
        const isEnd = i === steps.length - 1 && i === visSteps.length - 1;
        const isCurrent = i === visSteps.length - 1 && animStep >= 0;
        return (
          <g key={`s-${i}`}>
            <circle
              cx={cx}
              cy={cy}
              r={isStart ? 9 : isCurrent ? 8 : 5}
              fill={isStart ? '#005CAB' : isEnd ? '#198754' : '#6fb36f'}
              stroke={isCurrent ? '#198754' : 'none'}
              strokeWidth={2}
            />
            {(isStart || isEnd) && (
              <text
                x={cx + 8}
                y={cy + 4}
                style={{ fontSize: 10, fill: isStart ? '#005CAB' : '#198754', fontWeight: 700 }}
              >
                {isStart ? 'Début' : 'Cible A'}
              </text>
            )}
          </g>
        );
      })}

      {/* Condorcet winner badge */}
      {data.condorcet_winner_exists && (
        <text
          x={SVG_SIZE / 2}
          y={PAD - 6}
          textAnchor="middle"
          style={{ fontSize: 11, fill: '#198754', fontWeight: 700 }}
        >
          ★ Gagnant de Condorcet
        </text>
      )}
    </svg>
  );
};

// ── Main panel ────────────────────────────────────────────────────────────────

const PlottChaosPanel: React.FC = () => {
  const { t } = useTranslation();

  const [numVoters, setNumVoters] = useState(5);
  const [seed, setSeed] = useState(42);
  const sim = $api.useMutation('post', '/api/v2/theory/plott-chaos');
  const data: PlottData | null = (sim.data as PlottData | undefined) ?? null;
  const loading = sim.isPending;
  const error = sim.isError ? t('plott.error') : null;
  const [animStep, setAnimStep] = useState(-1);
  const [playing, setPlaying] = useState(false);
  const [showAlt, setShowAlt] = useState(false);
  const animRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const runSimulation = useCallback(
    (nv: number, s: number) => {
      setPlaying(false);
      setAnimStep(-1);
      setShowAlt(false);
      sim.mutate({
        body: {
          num_voters: nv,
          num_dimensions: 2,
          seed: s,
          target_policy: [0.6, 0.6],
          start_policy: [-0.6, -0.6],
          max_steps: 15,
        },
      });
      // eslint-disable-next-line react-hooks/exhaustive-deps
    },
    [t, sim]
  );

  const handleSimulate = () => runSimulation(numVoters, seed);

  // Animation
  useEffect(() => {
    if (animRef.current) clearInterval(animRef.current);
    if (!playing || !data) return;
    const total = data.chaos_path.steps.length - 1;
    animRef.current = setInterval(() => {
      setAnimStep((prev) => {
        if (prev >= total) {
          setPlaying(false);
          clearInterval(animRef.current!);
          return prev;
        }
        return prev + 1;
      });
    }, ANIM_MS);
    return () => {
      if (animRef.current) clearInterval(animRef.current);
    };
  }, [playing, data]);

  const handlePlay = () => {
    if (!data) return;
    if (animStep >= data.chaos_path.steps.length - 1) setAnimStep(0);
    setPlaying((p) => !p);
  };

  return (
    <div>
      {/* Controls */}
      <Row className="g-2 mb-3 items-end">
        <Col xs={12} md={4}>
          <label className="mb-1 inline-block text-sm mb-0">
            {t('plott.numVoters')}: <strong>{numVoters}</strong>
          </label>
          <Range
            min={3}
            max={21}
            step={2}
            value={numVoters}
            data-testid="voters-slider"
            onChange={(e) => setNumVoters(Number(e.target.value))}
          />
        </Col>
        <Col xs={12} md={3}>
          <label className="mb-1 inline-block text-sm mb-0">{t('plott.seed')}</label>
          <Control
            type="number"
            size="sm"
            value={seed}
            data-testid="seed-input"
            onChange={(e) => setSeed(Number(e.target.value))}
          />
        </Col>
        <Col xs="auto">
          <Button
            variant="primary"
            onClick={handleSimulate}
            disabled={loading}
            data-testid="simulate-btn"
          >
            {loading ? <Spinner size="sm" /> : t('plott.run')}
          </Button>
        </Col>
      </Row>

      {!data && !loading && !error && (
        <Alert variant="info" role="alert">
          {t('plott.prompt')}
        </Alert>
      )}
      {error && <Alert variant="danger">{error}</Alert>}

      {data && (
        <Row className="g-3">
          <Col xs={12} md={7}>
            {/* Status badge */}
            <div className="flex flex-wrap gap-2 mb-2">
              <Badge
                variant={data.condorcet_winner_exists ? 'success' : 'danger'}
                data-testid="condorcet-badge"
              >
                {data.condorcet_winner_exists ? t('plott.condorcetExists') : t('plott.noCondorcet')}
              </Badge>
              <Badge variant="secondary" data-testid="top-cycle-badge">
                {t('plott.topCycle')}: {data.top_cycle.size}/100 {t('plott.policies')}
              </Badge>
              {data.chaos_path.num_steps > 0 && (
                <Badge variant="info" data-testid="path-steps-badge">
                  {t('plott.pathSteps')}: {data.chaos_path.num_steps}
                </Badge>
              )}
            </div>

            {/* Map */}
            <ChaosMap data={data} animStep={animStep} showAlt={showAlt} />

            {/* Animation controls */}
            <div className="flex gap-2 mt-2 flex-wrap items-center">
              <Button
                size="sm"
                variant="outline-secondary"
                onClick={() => {
                  setAnimStep(0);
                  setPlaying(false);
                }}
              >
                ⏮
              </Button>
              <Button
                size="sm"
                variant={playing ? 'warning' : 'success'}
                data-testid="play-btn"
                onClick={handlePlay}
                disabled={data.chaos_path.num_steps === 0}
              >
                {playing ? '⏸' : '▶'} {t('plott.animatePath')}
              </Button>
              <Range
                data-testid="step-slider"
                min={0}
                max={Math.max(0, data.chaos_path.steps.length - 1)}
                value={animStep < 0 ? data.chaos_path.steps.length - 1 : animStep}
                onChange={(e) => {
                  setAnimStep(Number(e.target.value));
                  setPlaying(false);
                }}
                style={{ maxWidth: 120 }}
              />
            </div>
          </Col>

          <Col xs={12} md={5}>
            {/* Chaos demo */}
            <div className="font-semibold mb-2" style={{ fontSize: '0.85rem' }}>
              🎯 {t('plott.chaosDemo')}
            </div>

            <div
              className="border border-border rounded p-3 mb-3"
              style={{ background: '#f8f9fa' }}
            >
              <div style={{ fontSize: '0.8rem' }} className="mb-2">
                {t('plott.chaosExplain')}
              </div>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="success"
                  data-testid="show-path-a-btn"
                  onClick={() => {
                    setShowAlt(false);
                    setAnimStep(-1);
                  }}
                >
                  🟢 {t('plott.showPathA')}
                </Button>
                <Button
                  size="sm"
                  variant="warning"
                  data-testid="show-alt-btn"
                  onClick={() => setShowAlt(true)}
                >
                  🟠 {t('plott.showPathB')}
                </Button>
              </div>
              {showAlt && data.alternative_path.steps.length > 0 && (
                <Alert variant="warning" className="mt-2 mb-0 py-1" style={{ fontSize: '0.78rem' }}>
                  {t('plott.altPathFound', { n: data.alternative_path.steps.length - 1 })}
                </Alert>
              )}
            </div>

            {/* Agenda-setter explanation */}
            <Alert variant="secondary" style={{ fontSize: '0.78rem' }}>
              <strong>{t('plott.agendaTitle')}</strong> {t('plott.agendaDesc')}
            </Alert>

            {/* Pedagogical note */}
            <Alert variant="light" style={{ fontSize: '0.78rem', border: '1px solid #dee2e6' }}>
              {data.pedagogical_note}
            </Alert>
          </Col>
        </Row>
      )}
    </div>
  );
};

export default PlottChaosPanel;
